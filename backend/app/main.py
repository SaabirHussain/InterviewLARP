import os
import uuid
from pathlib import Path

import httpx
import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .llm import generate
from .mock import PRESETS, VOICES, best_fit, fit_score, mock_answer, mock_candidates, mock_evaluation, mock_job, mock_questions, rating_comparisons
from .models import Answer, AnswerRequest, CandidateBatch, EvaluateRequest, Evaluation, Job, JobRequest, QuestionRequest, Questions

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], send_default_pii=False, max_request_body_size="never", traces_sample_rate=0)
app = FastAPI(title="InterviewLARP")


class JDRequest(BaseModel):
    jd_text: str = Field(min_length=1, max_length=20000)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=6000)
    voice_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")


@app.get("/api/status")
def status():
    return {"mock": not bool(os.getenv("LLM_API_KEY")), "voice": bool(os.getenv("ELEVENLABS_API_KEY"))}


@app.get("/api/presets", response_model=list[Job])
def presets():
    return PRESETS


@app.post("/api/parse-jd", response_model=Job)
async def parse_jd(req: JDRequest):
    if not req.jd_text.strip():
        raise HTTPException(422, "Please enter a job description")
    return await generate(Job, "Extract the job accurately. Use 'Not specified' for missing fields. Include at least one skill.", req.model_dump(), lambda: mock_job(req.jd_text))


async def voice_ids():
    if os.getenv("ELEVENLABS_API_KEY"):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get("https://api.elevenlabs.io/v2/voices", headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}, params={"page_size": 20})
                r.raise_for_status()
                ids = list(dict.fromkeys(v["voice_id"] for v in r.json()["voices"]))
                if len(ids) >= 3:
                    return ids[:3]
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            pass
    return VOICES


@app.post("/api/candidates")
async def candidates(req: JobRequest):
    job = req.job.model_copy(update={"skills": req.job.skills or ["Problem solving"]})
    batch = await generate(CandidateBatch, "Assign three distinct archetypes with archetype_blurb consistent with attributes (Prepared One, Nervous Genius, Smooth Bluffer, Rambler, Under-seller). Generate 3 distinct fictional candidates with strongly varied attributes. At least one has larping >=8, smartness <=4, and a spectacular resume. Every fabricated claim must also appear on their resume. Give low-larping candidates 1 inflated claim and high-larping candidates 2 or 3. Make names and histories fresh.", {"job": job.model_dump(), "variation": str(uuid.uuid4())}, lambda: {"candidates": mock_candidates(job)})
    if len({c.archetype for c in batch.candidates}) != 3 or not any(c.attributes.larping >= 8 and c.attributes.smartness <= 4 for c in batch.candidates):
        batch = CandidateBatch(candidates=mock_candidates(job))
    voices = await voice_ids()
    for i, c in enumerate(batch.candidates):
        c.id = str(uuid.uuid4())
        c.voice_id = voices[i]
    return batch.candidates


@app.post("/api/questions", response_model=Questions)
async def questions(req: QuestionRequest):
    return await generate(Questions, "Include behavioural_tests, technical_tests and special.tests: concise explanations of what each question tests. Write concise, job-specific behavioural and technical question options. Special must be followup on a concrete previous answer in rounds 2-3 if transcript exists; otherwise probe a specific resume claim. Never reveal hidden attributes.", req.model_dump(), lambda: mock_questions(req))


@app.post("/api/answer", response_model=Answer)
async def answer(req: AnswerRequest):
    return await generate(Answer, "Exhibit the candidate archetype behaviours, without naming the archetype. You ARE this fictional candidate. Stay consistent with transcript and resume. Reply in 2-5 sentences, in first person. Mood low: curt/nervous with ums. Smartness controls technical depth. Charisma controls polish. High larping: confident bluffing that crumbles under specific follow-ups and resume probes about fabricated claims. Never mention numerical attributes or that this is a game.", req.model_dump(), lambda: mock_answer(req))


@app.post("/api/evaluate", response_model=Evaluation)
async def evaluate(req: EvaluateRequest):
    ids = {c.id for c in req.candidates}
    if len(ids) != 3 or req.hired_id not in ids or not set(req.transcripts).issubset(ids) or not set(req.ratings).issubset(ids):
        raise HTTPException(422, "Candidate IDs must be unique and match the hire and transcripts")
    best = best_fit(req.job, req.candidates)
    weakest = min(req.candidates, key=lambda c: fit_score(req.job, c)).id
    result = await generate(Evaluation, "Coach a STUDENT learning to perform better in their own interviews. Include exactly 3 dos from the strongest candidate and 3 donts from the weakest, each candidate_id and quote copied exactly from an answer, plus advice. If that candidate has no transcript, return an empty lesson list; never invent a quote. Include annotations keyed by every candidate id, one per turn in order, with tone good/bad/neutral, label and why_interviewers_notice anchored in that answer. Include rating_comparisons. Grade the interviewer based on their questions, evidence-seeking and coverage. Only mark a bluff caught if an answer actually exposed it and the question probed that claim. Be constructive and specific. Use the provided deterministic best fit; don't change it. Include one summary per candidate. Never invent questions not in the transcript.", {**req.model_dump(), "deterministic_best_fit_id": best}, lambda: mock_evaluation(req))
    if {s.id for s in result.candidate_summaries} != ids:
        result = mock_evaluation(req)
    valid_annotations = set(result.annotations) == ids and all(len(result.annotations[c.id]) == len(req.transcripts.get(c.id, [])) for c in req.candidates)
    valid_lessons = all(
        len(lessons) == (3 if req.transcripts.get(source) else 0)
        and all(lesson.candidate_id == source and any(lesson.quote == t.a for t in req.transcripts.get(source, [])) for lesson in lessons)
        for lessons, source in [(result.dos, best), (result.donts, weakest)]
    )
    if not valid_annotations or not valid_lessons:
        result = mock_evaluation(req)
    result.rating_comparisons = rating_comparisons(req)
    result.best_fit_id = best
    result.hired_was_best = best == req.hired_id
    if not result.hired_was_best:
        result.interviewer_score = min(result.interviewer_score, 70)
    return result


@app.post("/api/tts")
async def tts(req: TTSRequest):
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise HTTPException(503, "Voice unavailable; continue in text mode")
    client = httpx.AsyncClient(timeout=30)
    try:
        request = client.build_request("POST", f"https://api.elevenlabs.io/v1/text-to-speech/{req.voice_id}/stream", headers={"xi-api-key": key}, params={"output_format": "mp3_44100_128"}, json={"text": req.text, "model_id": "eleven_multilingual_v2"})
        response = await client.send(request, stream=True)
        response.raise_for_status()
    except httpx.HTTPError:
        await client.aclose()
        raise HTTPException(503, "Voice unavailable; continue in text mode")

    async def stream():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        except httpx.HTTPError:
            return
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(stream(), media_type="audio/mpeg")


@app.post("/api/stt")
async def stt(audio: UploadFile = File(...)):
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise HTTPException(503, "Microphone unavailable; type your question instead")
    content = await audio.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Recording must be under 10 MB")
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post("https://api.elevenlabs.io/v1/speech-to-text", headers={"xi-api-key": key}, data={"model_id": "scribe_v1", "tag_audio_events": "false"}, files={"file": (audio.filename or "recording.webm", content, audio.content_type or "audio/webm")})
            response.raise_for_status()
            text = response.json()["text"]
            if not isinstance(text, str):
                raise ValueError("Invalid transcript")
            return {"text": text}
    except (httpx.HTTPError, KeyError, ValueError):
        raise HTTPException(503, "Microphone unavailable; type your question instead")


DIST = ROOT / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    async def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "API route not found")
        return FileResponse(DIST / "index.html")
