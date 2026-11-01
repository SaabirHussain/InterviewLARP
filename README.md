# InterviewLARP

**Practice from the other side of the table.** A learning lab for students: play the interviewer to discover what makes a candidate stand out, then take those lessons into YOUR interviews. Set a role, interview three fictional AI candidates, rate your impressions, and unlock an evidence-backed playbook. Hiring is a secondary game mechanic. FastAPI + httpx backend, React + TypeScript + Vite frontend. Fully playable without keys.

## Student learning loop

- Each game includes three distinct hidden archetypes. Mock mode uses The Prepared One, The Nervous Genius and The Smooth Bluffer, consistent with their attributes and answer behaviours. Archetypes and blurbs appear only in feedback, never in interview or hire cards.
- Suggested questions include short explanations of what they test (`behavioural_tests`, `technical_tests`, `special.tests`).
- After every interview, including skips and timer expiry, rate Communication, Evidence/specifics, Honesty and Job fit on a 1–5 scale before advancing. Defaults are visibly 3; ratings are sent as a candidate-ID-keyed `ratings` map to `/api/evaluate`.
- Feedback starts with three do's from the strongest role-fit candidate and three don'ts from the weakest. Each quotes an exact answer. Skipping either candidate means no quotes/lessons for that side; we never invent transcript evidence. Short interviews may reuse a moment for different lessons.
- Feedback reveals archetypes, attributes and inflated claims, compares your ratings, and includes an annotated answer-by-answer replay (green/good, red/bad, neutral, plus text labels so colour isn't required). Hiring score remains below the learning content.
- Rating benchmarks are deterministic fiction: Communication = charisma/2, Evidence = smartness/2, Honesty = (11−larping)/2, rounded and clamped to 1–5. Job fit is the role-weighted fit score rounded and clamped to 1–5. Gaps of two points or more are flagged. These are teaching heuristics, not psychometrics or rules for judging real people.
- Mock annotations use answer-text heuristics; LLM coaching uses the same required Pydantic schema, retry-once and fallback path. API validation rejects invented lesson quotes/misaligned replay arrays; rating truth is always recalculated from the hidden profile. No live provider credentials are required.

### Local illustrated avatars and license

Avatars are SVG data URIs generated locally using `@dicebear/core` and `@dicebear/collection` v9, seeded by candidate ID/name. No avatar service/network calls. The **Avataaars** style by Pablo Stanley is [free for personal and commercial use](https://avataaars.com/), as confirmed by [DiceBear's style/license page](https://www.dicebear.com/styles/avataaars/); DiceBear's JS packages are MIT licensed. Low mood maps to concerned mouths/sad eyebrows, higher mood to smiling mouths. Appearance is fictional and not a measure of competence.

## Setup and development

Requires Python 3.10+ and Node 20 LTS. With [nvm](https://github.com/nvm-sh/nvm), run `nvm install 20 && nvm use 20` if Node isn't available.

From the repository root:

```sh
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
cd frontend
npm ci
```

Terminal one (from the root, virtualenv activated):

```sh
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal two:

```sh
cd frontend
npm run dev -- --port 5173
```

Open http://localhost:5173. Vite proxies `/api` to backend port 8000. API docs: http://localhost:8000/docs. Restart the backend after editing `.env`. The root `.env` is loaded by both backend and Vite; only `VITE_` variables are public.

## Optional model providers

Leave `LLM_API_KEY` blank for mock mode. The provider-agnostic client appends `/chat/completions` to `LLM_BASE_URL`, uses Bearer authentication, and reads `choices[0].message.content`. Keys stay server-side. Never prefix API keys with `VITE_`.

### Featherless

```dotenv
LLM_BASE_URL=https://api.featherless.ai/v1
LLM_API_KEY=your_featherless_key
LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
```

Request/response format verified from [official completions docs](https://featherless.ai/docs/completions): `model`, `messages`, `temperature`, `max_tokens`. Default model verified on the [official model catalog](https://featherless.ai/models); availability may depend on your plan.

### Google Gemini's OpenAI-compatible endpoint

```dotenv
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_API_KEY=your_google_ai_studio_key
LLM_MODEL=gemini-flash-lite-latest
```

Base URL and Bearer-auth format verified from [Google's official compatibility docs](https://ai.google.dev/gemini-api/docs/openai). Use `gemini-flash-lite-latest`: `gemini-2.5-flash` returns 404 for new API keys. Quotas, regional availability and model lifecycles apply; check [current pricing](https://ai.google.dev/gemini-api/docs/pricing). Thinking tokens consume completion budget and can cause JSON retry/fallback.

Every model output is requested as JSON, extracted from fenced/prose-wrapped objects, Pydantic-validated, retried once on failure, then replaced with a playable mock. The header indicates provider configuration, not guaranteed live health. Mock JD parsing picks a canned role and preserves an input excerpt; refine it on the editable brief screen.

## Free browser voice (default) and optional ElevenLabs upgrade

No ElevenLabs key is needed for voice. Candidate intros (after clicking **Bring in candidate**) and answers use the browser's `speechSynthesis`. We prefer English voices, listen for asynchronous `voiceschanged`, and select different installed voices for the three candidates when available. Distinct pitch/rate profiles and mood adjustments keep delivery varied even on systems with fewer than three voices. Low mood sounds slower/lower; high mood brighter. **Mute/Unmute** stops current speech and controls future utterances; it does not replay old answers. Moving to another screen/candidate cancels speech and recording. Avatar motion follows actual speech start/end events and respects reduced-motion preferences. Text appears immediately, independently of audio.

Hold the mic (pointer or Space key), release to finish, then edit the question before sending. Browser `SpeechRecognition` / `webkitSpeechRecognition` displays interim results in the question input. **Chrome/Edge work best for voice input**; unsupported browsers show a disabled mic with “Voice input works in Chrome/Edge — type instead”. Microphone permission and localhost/HTTPS are required. Recognition availability also depends on browser/network service support: browser voice has no app API cost, but recognition may send audio to the browser vendor's service and is not guaranteed offline. Permission/service errors retain the typed-question path. Browsers without speech synthesis remain fully playable in text.

If `/api/status` reports `voice: true` (`ELEVENLABS_API_KEY` set), the existing ElevenLabs paths take priority. A failed TTS request/playback falls back to browser speech for that same utterance. While recording for ElevenLabs, browser recognition also runs when supported, retaining an editable fallback transcript if `/api/stt` fails. Without browser recognition, an STT failure asks you to retry/type rather than claiming a transcript exists. Official ElevenLabs docs:

- [List voices](https://elevenlabs.io/docs/api-reference/voices/search): `GET /v2/voices`, `xi-api-key`, `voices[].voice_id`. Assigns three distinct voices with premade IDs as fallback.
- [Stream TTS](https://elevenlabs.io/docs/api-reference/text-to-speech/stream): `POST /v1/text-to-speech/{voice_id}/stream`, JSON `text`, `model_id=eleven_multilingual_v2`, query `output_format=mp3_44100_128`.
- [Scribe STT](https://elevenlabs.io/docs/api-reference/speech-to-text/convert): `POST /v1/speech-to-text`, multipart `file`, `model_id=scribe_v1`, response `text`.

Our `/api/stt` accepts multipart field **`audio`**, forwarding it as ElevenLabs **`file`**. Backend TTS/STT still return clean 503s without a key; the frontend uses browser voice instead of calling them. Live audible output and vendor recognition/ElevenLabs services require a real browser/device and are not validated by headless speech spies.

## Optional Sentry monitoring

Both SDKs are installed but **not initialized unless configured**:

```dotenv
SENTRY_DSN=
VITE_SENTRY_DSN=
```

`SENTRY_DSN` enables backend error monitoring at process startup. `VITE_SENTRY_DSN` is a public frontend project DSN read at **build time**; rebuild after changing it (restart Vite in development). Neither is an API secret. Leave both empty for no monitoring. Frontend always has a friendly React ErrorBoundary even when Sentry is disabled. No replay, tracing or default PII collection is enabled; backend request-body capture is disabled. Enabling monitoring sends error diagnostics to your Sentry project. Delivery has not been tested without a configured project.

Initialization APIs verified from [Sentry FastAPI](https://docs.sentry.io/platforms/python/integrations/fastapi/) and [Sentry React](https://docs.sentry.io/platforms/javascript/guides/react/) official docs. Production source-map uploads are not configured.

## Playing

1. Paste a JD or pick one of four preset jobs.
2. Edit the brief; choose full (5:00) or demo (1:30) time. Candidates prefetch immediately here. Résumés reflect the original brief; edits guide subsequent questions.
3. Bring candidates in to start their timers. Ask behavioural, technical, résumé/follow-up questions, or your own. After three answers, click Next candidate. Timer expiry automatically advances after an in-flight answer finishes. Skip is available for demos.
4. Review résumés/transcripts and hire; see the score, hidden attributes, inflated claims, caught/missed bluffs and tips.
5. Try again prepares new candidate identities for the same job. New job resets setup.

Each game samples three distinct archetypes on the server from eight: The Prepared One, The Nervous Genius, The Smooth Bluffer, The Rambler, The Under-seller, The Idiot, The Cocky One and The Casual One. Individual games can overlap; repeated games are not guaranteed disjoint. The server supplies required archetypes, consistent stat profiles and answer-style guidance to the model, then enforces the assigned types and stats on the response. Mock mode uses the same sampling and has distinct answers for every type/question kind. The Idiot is realistically unprepared, the Cocky One makes confident mistakes, and the Casual One mixes useful substance with slang that may feel authentic or unprofessional. Feedback reveals the type and offers advice; these are fictional behaviours, not labels for judging real students. Gemini sees the trait as `making_stuff_up`; API fields and UI “Larping / bluffing” wording stay unchanged.

Best fit is deterministic: `0.60 × smartness + 0.20 × mood + 0.20 × charisma − 0.35 × larping`. People-facing role titles (barista/community/sales/customer) use `0.25/0.30/0.45` weights instead. ID breaks ties. The LLM writes narrative but cannot override the best-fit result. Mock coaching uses question/probe heuristics, not semantic truth detection. This is practice, not a real hiring assessment.

## Checks

```sh
cd backend
../.venv/bin/pytest
cd ../frontend
npm run typecheck
npm run build
```

Tests cover JSON parsing/validation, missing keys, provider retries, configurable URLs, deterministic role-sensitive fit, varied candidates, empty/invalid input, full mock flow and voice failures. Build includes TypeScript checking; no lint command is configured.

## Production: one service

```sh
cd frontend
npm ci
npm run build
cd ../backend
../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Build **before** starting uvicorn: FastAPI then serves `frontend/dist` alongside `/api/*`. `render.yaml` describes one Python web service, building the frontend using Node 20 and binding Render's `$PORT`. It has **not been deployed**. Configure optional keys/DSNs in Render or leave blank for mock/no-monitoring mode.

## Layout

```text
.env.example                 Provider and monitoring config
render.yaml                  Single-service deployment blueprint
backend/
  requirements.txt, pytest.ini
  app/{main,models,llm,mock}.py
  tests/test_app.py
frontend/
  package.json, package-lock.json
  index.html, tsconfig.json, vite.config.ts
  src/{main,App}.tsx
  src/{types.ts,instrument.ts,vite-env.d.ts,style.css}
```

Hackathon limitations: unauthenticated, client-held game state, no persistence. Hidden attributes are hidden in the UI, not from developer tools. Do not store sensitive applicant information. Optional Google Fonts have system-font fallbacks. Before opening to untrusted traffic, add authentication, rate limits and edge request-body limits.
