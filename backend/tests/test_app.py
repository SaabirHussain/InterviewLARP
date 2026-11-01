import asyncio
import json
import os
import subprocess
import sys

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app import llm
from app.main import app
from app.mock import PRESETS, best_fit, mock_candidates, mock_evaluation, mock_answer
from app.models import Answer, AnswerRequest, EvaluateRequest, Resume, Turn


@pytest.fixture(autouse=True)
def no_keys(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)


@pytest.mark.parametrize("text", ['{"answer":"ok"}', '```json\n{"answer":"ok"}\n```', 'Prose {"answer":"ok","nested":{"x":"}"}} trailing {"ignored":1}'])
def test_json_parsing(text):
    assert llm.parse_json(text)["answer"] == "ok"


@pytest.mark.parametrize("text", ["", "```json\nnope```", "{broken}"])
def test_bad_json(text):
    with pytest.raises(ValueError):
        llm.parse_json(text)


def test_schema_validation():
    with pytest.raises(ValidationError):
        Answer.model_validate(llm.parse_json('{"answer":""}'))
    with pytest.raises(ValidationError):
        Resume(education="Example", experience=[], skills=[], projects=[])


def test_missing_key_fallback():
    assert asyncio.run(llm.generate(Answer, "", {}, lambda: {"answer": "mock"})).answer == "mock"


@pytest.mark.parametrize("failure", ["invalid_json", "invalid_schema", "http_error"])
def test_provider_failure_retries_once(monkeypatch, failure):
    monkeypatch.setenv("LLM_API_KEY", "test-not-a-real-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("LLM_MODEL", "example-model")
    requests = []

    def handler(request):
        requests.append(request)
        assert str(request.url) == "https://example.test/v1/chat/completions"
        assert json.loads(request.content)["model"] == "example-model"
        if failure == "http_error":
            return httpx.Response(429)
        return httpx.Response(200, json={"choices": [{"message": {"content": "not JSON" if failure == "invalid_json" else '{"answer":""}'}}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler)))
    assert asyncio.run(llm.generate(Answer, "", {}, lambda: {"answer": "safe"})).answer == "safe"
    assert len(requests) == 2


def test_provider_success(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-not-a-real-key")
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": [{"message": {"content": '```json\n{"answer":"live"}\n```'}}]}))
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: original(transport=transport))
    assert asyncio.run(llm.generate(Answer, "", {}, lambda: {"answer": "safe"})).answer == "live"


def test_best_fit_deterministic_and_role_sensitive():
    cs = mock_candidates(PRESETS[0])
    smart = next(c for c in cs if c.attributes.smartness == 9)
    warm = next(c for c in cs if c.attributes.mood == 9)
    assert best_fit(PRESETS[0], cs) == smart.id
    assert best_fit(PRESETS[0], list(reversed(cs))) == smart.id
    assert best_fit(PRESETS[1], cs) == warm.id
    with pytest.raises(ValueError):
        best_fit(PRESETS[0], [])


def test_candidates_new_and_varied():
    a, b = mock_candidates(PRESETS[0]), mock_candidates(PRESETS[0])
    assert not {c.id for c in a} & {c.id for c in b}
    assert len({c.voice_id for c in a}) == 3
    assert any(c.attributes.larping >= 8 and c.attributes.smartness <= 4 for c in a)
    assert all(set(c.fabricated_claims).issubset(c.resume.experience) for c in a)
    assert len({c.archetype for c in a}) == 3
    assert all(c.archetype_blurb for c in a)
    assert next(c for c in a if c.attributes.larping > 7).archetype == "The Smooth Bluffer"


@pytest.mark.parametrize('kind', ['behavioural', 'technical', 'resume', 'followup', 'custom'])
def test_mock_answers_vary_by_kind_and_round_deterministically(kind):
    for candidate in mock_candidates(PRESETS[0]):
        answers = []
        transcript = []
        for round_number in range(3):
            req = AnswerRequest(job=PRESETS[0], candidate=candidate, transcript=transcript, question='Tell me more.', kind=kind)
            answer = mock_answer(req)['answer']
            assert mock_answer(req)['answer'] == answer
            answers.append(answer)
            transcript.append(Turn(q=req.question, a=answer, kind=kind))
        assert len(set(answers)) == 3
        across_kinds = [mock_answer(AnswerRequest(job=PRESETS[0], candidate=candidate, question='Tell me more.', kind=k))['answer'] for k in ['behavioural', 'technical', 'resume', 'followup', 'custom']]
        assert len(set(across_kinds)) == 5


def test_mock_score_rewards_balanced_coverage_and_probing():
    candidates = mock_candidates(PRESETS[0])
    req = EvaluateRequest(job=PRESETS[0], candidates=candidates, transcripts={}, hired_id=best_fit(PRESETS[0], candidates))
    behavioural = Turn(q="Tell me about a disagreement.", a="We compromised.", kind="behavioural")
    technical = Turn(q="How would you debug this?", a="I would test it.", kind="technical")
    probe = Turn(q="What evidence supports your resume claim?", a="I overstated it.", kind="resume")
    empty_score = mock_evaluation(req).interviewer_score
    req.transcripts = {c.id: [behavioural] * 3 for c in candidates}
    repeated_score = mock_evaluation(req).interviewer_score
    req.transcripts = {c.id: [behavioural, technical, behavioural] for c in candidates}
    unprobed_score = mock_evaluation(req).interviewer_score
    req.transcripts = {c.id: [behavioural, technical, probe] for c in candidates}
    assert empty_score < repeated_score < unprobed_score < mock_evaluation(req).interviewer_score == 100
    req.transcripts = {candidates[0].id: [behavioural, technical, probe]}
    assert mock_evaluation(req).interviewer_score < unprobed_score
    req.transcripts = {c.id: [behavioural, technical, probe.model_copy(update={"kind": "followup"})] for c in candidates}
    assert mock_evaluation(req).interviewer_score == 100
    req.hired_id = next(c.id for c in candidates if c.id != req.hired_id)
    assert mock_evaluation(req).interviewer_score == 70
    req.transcripts = {}
    assert mock_evaluation(req).interviewer_score == 1


@pytest.mark.parametrize("hire_best,expected", [(False, 70), (True, 100)])
def test_evaluate_caps_generated_score_for_wrong_hire(monkeypatch, hire_best, expected):
    candidates = mock_candidates(PRESETS[0])
    best = best_fit(PRESETS[0], candidates)
    hired = best if hire_best else next(c.id for c in candidates if c.id != best)
    req = EvaluateRequest(job=PRESETS[0], candidates=candidates, transcripts={}, hired_id=hired)

    async def generated(*args, **kwargs):
        return mock_evaluation(req).model_copy(update={"interviewer_score": 100, "hired_was_best": True})

    monkeypatch.setattr("app.main.generate", generated)
    response = TestClient(app).post("/api/evaluate", json=req.model_dump())
    assert response.status_code == 200
    assert response.json()["interviewer_score"] == expected
    assert response.json()["hired_was_best"] == hire_best


def test_complete_mock_flow():
    client = TestClient(app)
    job = client.get("/api/presets").json()[0]
    assert client.post("/api/parse-jd", json={"jd_text": "Hiring a Python intern"}).status_code == 200
    candidates = client.post("/api/candidates", json={"job": job}).json()
    transcripts = {}
    for c in candidates:
        transcript = []
        for round_number in range(1, 4):
            q = client.post("/api/questions", json={"job": job, "candidate": c, "transcript": transcript, "round": round_number}).json()
            assert q["special"]["kind"] == ("resume" if round_number == 1 else "followup")
            assert all(q[k] for k in ["behavioural_tests", "technical_tests"])
            assert q["special"]["tests"]
            a = client.post("/api/answer", json={"job": job, "candidate": c, "transcript": transcript, "question": q["special"]["text"]})
            assert a.status_code == 200
            transcript.append({"q": q["special"]["text"], "a": a.json()["answer"], "kind": q["special"]["kind"]})
        transcripts[c["id"]] = transcript
        assert len({t['a'] for t in transcript}) == 3
    ratings = {c['id']: dict(communication=5, evidence=5, honesty=5, job_fit=5) for c in candidates}
    payload = {"job": job, "candidates": candidates, "transcripts": transcripts, "ratings": ratings, "hired_id": candidates[0]["id"]}
    result = client.post("/api/evaluate", json=payload)
    assert result.status_code == 200
    assert 1 <= result.json()["interviewer_score"] <= 100
    assert len(result.json()["candidate_summaries"]) == 3
    body = result.json()
    assert len(body['dos']) == len(body['donts']) == 3
    for lesson in body['dos'] + body['donts']:
        assert lesson['quote'] in [t['a'] for t in transcripts[lesson['candidate_id']]]
    assert all(len(body['annotations'][c['id']]) == 3 for c in candidates)
    bluffer = next(c for c in candidates if c['attributes']['larping'] > 7)
    assert body['annotations'][bluffer['id']][0]['tone'] == 'bad'
    comparison = next(r for r in body['rating_comparisons'] if r['id'] == bluffer['id'])
    assert comparison['truth']['honesty'] == 1
    assert any('Honesty' in flag for flag in comparison['flags'])
    empty = client.post("/api/evaluate", json={**payload, "transcripts": {}})
    assert empty.status_code == 200
    assert empty.json()["best_questions"] == []
    assert empty.json()['dos'] == empty.json()['donts'] == []
    assert all(notes == [] for notes in empty.json()['annotations'].values())
    assert client.post("/api/evaluate", json={**payload, "hired_id": "wrong"}).status_code == 422
    assert client.post('/api/evaluate', json={**payload, 'ratings': {'wrong': ratings[candidates[0]['id']]}}).status_code == 422
    assert client.post('/api/evaluate', json={**payload, 'ratings': {candidates[0]['id']: dict(communication=6, evidence=1, honesty=1, job_fit=1)}}).status_code == 422


def test_invalid_generated_learning_content_falls_back(monkeypatch):
    candidates = mock_candidates(PRESETS[0])
    req = EvaluateRequest(job=PRESETS[0], candidates=candidates, transcripts={c.id: [Turn(q='Evidence?', a='A real answer.', kind='resume')] for c in candidates}, hired_id=candidates[0].id)
    async def generated(*args, **kwargs):
        result = mock_evaluation(req)
        result.dos[0].quote = 'Invented quote'
        return result
    monkeypatch.setattr('app.main.generate', generated)
    result = TestClient(app).post('/api/evaluate', json=req.model_dump()).json()
    assert result['dos'][0]['quote'] == 'A real answer.'
    assert all(r['user'] is None for r in result['rating_comparisons'])


def test_new_fields_require_validation_and_fallback(monkeypatch):
    from app.models import Evaluation, Rating
    candidates = mock_candidates(PRESETS[0])
    req = EvaluateRequest(job=PRESETS[0], candidates=candidates, transcripts={}, hired_id=candidates[0].id)
    result = mock_evaluation(req)
    req.transcripts = {result.best_fit_id: [Turn(q='An example?', a='I checked my work.', kind='technical')]}
    partial = mock_evaluation(req)
    assert len(partial.dos) == 3 and partial.donts == []
    req.transcripts = {}
    req.ratings = {r.id: r.truth for r in result.rating_comparisons}
    assert all(not r.flags for r in mock_evaluation(req).rating_comparisons)
    with pytest.raises(ValidationError):
        Rating(communication=0, evidence=3, honesty=3, job_fit=3)
    monkeypatch.setenv('LLM_API_KEY', 'not-a-real-key')
    original = httpx.AsyncClient
    malformed = result.model_dump()
    del malformed['annotations']
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(malformed)}}]}))
    monkeypatch.setattr(llm.httpx, 'AsyncClient', lambda **kwargs: original(transport=transport))
    generated = asyncio.run(llm.generate(Evaluation, '', {}, lambda: mock_evaluation(req)))
    assert generated.annotations == {c.id: [] for c in candidates}


def test_empty_and_invalid_requests():
    client = TestClient(app)
    assert client.post("/api/parse-jd", json={"jd_text": ""}).status_code == 422
    assert client.post("/api/parse-jd", json={"jd_text": "  "}).status_code == 422
    assert client.post("/api/answer", json={}).status_code == 422
    job = PRESETS[0].model_copy(update={"skills": []}).model_dump()
    assert client.post("/api/candidates", json={"job": job}).status_code == 200


def test_voice_missing_key_returns_503():
    client = TestClient(app)
    assert not client.get("/api/status").json()["voice"]
    assert client.post("/api/tts", json={"text": "hi", "voice_id": "example"}).status_code == 503
    assert client.post("/api/stt", files={"audio": ("test.webm", b"audio", "audio/webm")}).status_code == 503


def test_voice_provider_failure_returns_503(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-not-a-real-key")
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(lambda _: httpx.Response(401))))
    client = TestClient(app)
    assert client.post("/api/tts", json={"text": "hi", "voice_id": "example"}).status_code == 503
    assert client.post("/api/stt", files={"audio": ("test.webm", b"audio", "audio/webm")}).status_code == 503


@pytest.mark.parametrize("dsn,expected", [("", 0), ("https://public@example.test/1", 1)])
def test_sentry_initializes_only_with_dsn(dsn, expected):
    code = "from unittest.mock import patch\nwith patch('sentry_sdk.init') as init:\n import app.main\n print(init.call_count)"
    result = subprocess.check_output([sys.executable, "-c", code], env={**os.environ, "SENTRY_DSN": dsn}, text=True)
    assert int(result.strip()) == expected


def test_production_static_and_unknown_api():
    from app.main import DIST

    if not DIST.is_dir():
        pytest.skip("Frontend build not present")
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert "InterviewLARP" in client.get("/").text
    assert client.get("/api/not-a-route").status_code == 404
