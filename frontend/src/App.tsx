import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  BriefcaseBusiness,
  Check,
  CheckCheck,
  ChevronRight,
  Clock3,
  Coffee,
  FileText,
  Mic,
  RotateCcw,
  Send,
  ShieldQuestion,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import type {
  Candidate,
  Evaluation,
  Job,
  Questions,
  Turn,
  Rating,
} from "./types";
import { createAvatar } from "@dicebear/core";
import { avataaars } from "@dicebear/collection";
import { useInterviewVoice } from "./useInterviewVoice";

async function api<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(
    "/api/" + path,
    body === undefined
      ? { signal }
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal,
        },
  );
  if (!response.ok)
    throw new Error(
      `Something went wrong (${response.status}). Please try again.`,
    );
  return response.json();
}
function Portrait({
  candidate,
  prominent = false,
  talking = false,
}: {
  candidate: Candidate;
  prominent?: boolean;
  talking?: boolean;
}) {
  const nervous = candidate.attributes.mood < 5;
  const src = createAvatar(avataaars, {
    seed: candidate.id + candidate.name,
    mouth: [nervous ? "concerned" : "smile"],
    eyebrows: [nervous ? "sadConcerned" : "defaultNatural"],
    eyes: ["default"],
    backgroundColor: ["dcece7"],
    accessoriesProbability: 0,
  }).toDataUri();
  return (
    <img
      className={
        "portrait" +
        (prominent ? " prominent" : "") +
        (talking ? " talking" : "")
      }
      src={src}
      alt={`Illustrated portrait of ${candidate.name}`}
    />
  );
}
const ratingLabels = {
  communication: "Communication",
  evidence: "Evidence / specifics",
  honesty: "Honesty",
  job_fit: "Job fit",
};
const defaultRating: Rating = {
  communication: 3,
  evidence: 3,
  honesty: 3,
  job_fit: 3,
};

function Resume({
  candidate,
  compact = false,
}: {
  candidate: Candidate;
  compact?: boolean;
}) {
  return (
    <div className={"resume " + (compact ? "compact" : "")}>
      <label>EDUCATION</label>
      <p>{candidate.resume.education}</p>
      <label>EXPERIENCE</label>
      {candidate.resume.experience.map((x, i) => (
        <p key={i}>{x}</p>
      ))}
      <label>SKILLS</label>
      <div className="chips">
        {candidate.resume.skills.map((x, i) => (
          <span key={i}>{x}</span>
        ))}
      </div>
      {!compact && (
        <>
          <label>PROJECTS</label>
          {candidate.resume.projects.map((x, i) => (
            <p key={i}>{x}</p>
          ))}
        </>
      )}
    </div>
  );
}

export default function App() {
  const [screen, setScreen] = useState("input");
  const [presets, setPresets] = useState<Job[]>([]);
  const [showPresets, setShowPresets] = useState(false);
  const [jd, setJd] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [transcripts, setTranscripts] = useState<Record<string, Turn[]>>({});
  const [ratings, setRatings] = useState<Record<string, Rating>>({});
  const [index, setIndex] = useState(0);
  const [entered, setEntered] = useState(false);
  const [duration, setDuration] = useState(300);
  const [seconds, setSeconds] = useState(300);
  const [questions, setQuestions] = useState<Questions | null>(null);
  const [questionError, setQuestionError] = useState(false);
  const [custom, setCustom] = useState("");
  const [pending, setPending] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [error, setError] = useState("");
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [hired, setHired] = useState("");
  const [mode, setMode] = useState({ mock: true, voice: false });
  const [delivering, setDelivering] = useState(false);
  const deliveryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const generation = useRef(0);
  const answerRequest = useRef<AbortController | null>(null);
  const {
    speak,
    stopSpeech: stopAudio,
    cancelRecording,
    beginRecord,
    endRecord,
    muted,
    toggleMute,
    talking,
    recording,
    transcribing,
    notice,
    micAvailable,
    micTooltip,
  } = useInterviewVoice(mode.voice, setCustom);
  const chatEnd = useRef<HTMLDivElement>(null);
  const candidate = candidates[index];
  const turns = candidate ? transcripts[candidate.id] || [] : [];
  const round = turns.length + 1;

  function stopDelivery() {
    if (deliveryTimer.current) clearTimeout(deliveryTimer.current);
    deliveryTimer.current = null;
    setDelivering(false);
  }

  function deliver(text: string) {
    stopDelivery();
    if (!text.trim()) return;
    setDelivering(true);
    const duration = Math.min(
      30000,
      Math.max(1800, text.trim().split(/\s+/).length * 350),
    );
    deliveryTimer.current = setTimeout(() => setDelivering(false), duration);
  }

  useEffect(
    () => () => {
      if (deliveryTimer.current) clearTimeout(deliveryTimer.current);
      answerRequest.current?.abort();
    },
    [],
  );

  useEffect(() => {
    stopAudio();
    cancelRecording();
    stopDelivery();
  }, [screen, candidate?.id]);

  useEffect(() => {
    api<Job[]>("presets")
      .then(setPresets)
      .catch(() => setError("Could not load presets. Refresh to try again."));
    api<typeof mode>("status")
      .then(setMode)
      .catch(() => {});
  }, []);
  useEffect(() => {
    chatEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [pending, turns.length]);
  async function loadCandidates(value: Job) {
    const requestId = ++generation.current;
    setLoadingCandidates(true);
    setCandidates([]);
    try {
      const result = await api<Candidate[]>("candidates", { job: value });
      if (requestId === generation.current) setCandidates(result);
    } catch (e) {
      if (requestId === generation.current) setError((e as Error).message);
    } finally {
      if (requestId === generation.current) setLoadingCandidates(false);
    }
  }
  function summarize(value: Job) {
    setJob(value);
    setError("");
    setScreen("summary");
    void loadCandidates(value);
  }
  async function analyze() {
    setBusy(true);
    setError("");
    try {
      summarize(await api<Job>("parse-jd", { jd_text: jd }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function start() {
    setTranscripts({});
    setRatings({});
    setIndex(0);
    setEntered(false);
    setQuestions(null);
    setSeconds(duration);
    setScreen("interview");
    setError("");
    setPending("");
    setCustom("");
  }
  function next() {
    answerRequest.current?.abort();
    answerRequest.current = null;
    setBusy(false);
    stopAudio();
    stopDelivery();
    cancelRecording();
    setEntered(false);
    setQuestions(null);
    setPending("");
    setCustom("");
    setError("");
    setSeconds(duration);
    setScreen("rating");
  }
  useEffect(() => {
    if (screen !== "interview" || !entered || !candidate || round > 3) return;
    let cancelled = false;
    setQuestions(null);
    setQuestionError(false);
    api<Questions>("questions", { job, candidate, transcript: turns, round })
      .then((q) => {
        if (!cancelled) setQuestions(q);
      })
      .catch(() => {
        if (!cancelled) setQuestionError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [screen, entered, candidate?.id, turns.length]);
  useEffect(() => {
    if (screen !== "interview" || !entered || round > 3) return;
    const timer = window.setInterval(
      () => setSeconds((s) => Math.max(0, s - 1)),
      1000,
    );
    return () => clearInterval(timer);
  }, [screen, entered, round]);
  useEffect(() => {
    if (screen === "interview" && entered && seconds === 0 && !busy) next();
  }, [seconds, busy, screen, entered]);

  async function ask(text: string, kind: string) {
    if (busy || !text.trim() || round > 3 || seconds === 0) return;
    stopAudio();
    stopDelivery();
    cancelRecording();
    setBusy(true);
    setError("");
    setPending(text);
    setCustom("");
    const controller = new AbortController();
    answerRequest.current = controller;
    try {
      const result = await api<{ answer: string }>("answer", {
        job,
        candidate,
        transcript: turns,
        question: text,
        kind,
      }, controller.signal);
      if (answerRequest.current !== controller) return;
      setTranscripts((ts) => ({
        ...ts,
        [candidate.id]: [
          ...(ts[candidate.id] || []),
          { q: text, a: result.answer, kind },
        ],
      }));
      deliver(result.answer);
      void speak(result.answer, candidate, index);
    } catch (e) {
      if (answerRequest.current !== controller) return;
      setError((e as Error).message);
      setCustom(text);
    } finally {
      if (answerRequest.current === controller) {
        answerRequest.current = null;
        setPending("");
        setBusy(false);
      }
    }
  }
  async function hire(id: string) {
    setBusy(true);
    setError("");
    setHired(id);
    try {
      setEvaluation(
        await api<Evaluation>("evaluate", {
          job,
          candidates,
          transcripts,
          ratings,
          hired_id: id,
        }),
      );
      setScreen("feedback");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const steps = ["The role", "The interviews", "The decision", "The reveal"];
  const step =
    screen === "input" || screen === "summary"
      ? 0
      : screen === "interview" || screen === "rating"
        ? 1
        : screen === "hire"
          ? 2
          : 3;

  return (
    <>
      <header>
        <a className="brand" href="/" aria-label="InterviewLARP home">
          <span className="brand-icon">
            <AudioLines size={20} />
          </span>
          Interview<span>LARP</span>
          <sup>BETA</sup>
        </a>
        <div className="header-right">
          <span className="status-dot" />
          {mode.mock ? "Mock mode · no keys needed" : "AI-powered practice"}
          <span className="divider" />A little role-play. A real skill.
        </div>
      </header>
      <main>
        <nav className="steps">
          {steps.map((s, i) => (
            <div
              key={s}
              className={i === step ? "active" : i < step ? "done" : ""}
            >
              <span>{i < step ? <Check size={13} /> : `0${i + 1}`}</span>
              {s}
              {i < 3 && <ChevronRight size={14} />}
            </div>
          ))}
        </nav>
        {error && (
          <div role="alert" className="error">
            {error}
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        )}

        {screen === "input" && (
          <>
            <section className="hero">
              <div className="eyebrow">
                <span /> THE OTHER SIDE OF THE TABLE
              </div>
              <h1>
                Great résumé.
                <br />
                But can they <span>actually do it?</span>
                <svg viewBox="0 0 460 15" aria-hidden="true">
                  <path d="M3 10 Q210 -3 454 7" />
                </svg>
              </h1>
              <p>
                A practice lab for students: play the interviewer, meet three AI
                candidates, and discover what to do in YOUR next interview.
              </p>
            </section>
            <div className="landing-grid">
              <section className="panel job-panel">
                <div className="panel-title">
                  <span className="soft-icon">
                    <BriefcaseBusiness size={19} />
                  </span>
                  <div>
                    <h2>First, who are we hiring?</h2>
                    <p>Set the scene with a job description.</p>
                  </div>
                  <span className="tag">STEP 01</span>
                </div>
                <label htmlFor="jd">JOB DESCRIPTION</label>
                <textarea
                  id="jd"
                  className="jd"
                  value={jd}
                  onChange={(e) => setJd(e.target.value)}
                  placeholder={
                    "Paste a job description here…\n\nThe role, the must-haves, the “nice to haves.” We’ll turn it into your interview brief."
                  }
                  maxLength={20000}
                />
                <div className="input-footer">
                  <span>
                    <ShieldQuestion size={14} /> Any role. Any industry.
                  </span>
                  <span>{jd.length.toLocaleString()} / 20,000</span>
                </div>
                <button
                  className="primary wide"
                  disabled={!jd.trim() || busy}
                  onClick={analyze}
                >
                  {busy ? "Reading the brief…" : "Analyze job description"}
                  <ArrowRight size={17} />
                </button>
                <div className="or">
                  <span />
                  OR, KEEP IT SIMPLE
                  <span />
                </div>
                <button
                  className="preset-toggle"
                  onClick={() => setShowPresets(!showPresets)}
                >
                  Skip — pick a preset role
                  <ArrowUpRight size={17} />
                </button>
                {showPresets && (
                  <div className="preset-grid">
                    {presets.map((p, i) => (
                      <button key={p.title} onClick={() => summarize(p)}>
                        {i === 1 ? (
                          <Coffee size={18} />
                        ) : (
                          <BriefcaseBusiness size={18} />
                        )}
                        <strong>{p.title}</strong>
                        <span>
                          {p.company} <ArrowRight size={14} />
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </section>
              <aside className="how-panel">
                <div className="eyebrow">YOUR NEXT 10 MINUTES</div>
                <h2>
                  A hiring simulation.
                  <br />
                  With a plot twist.
                </h2>
                {[
                  {
                    icon: <FileText size={19} />,
                    title: "Set the role",
                    text: "Bring a job description, or borrow one of ours.",
                  },
                  {
                    icon: <Users size={19} />,
                    title: "Meet your candidates",
                    text: "Three personalities. Three rounds each. Not everyone is what they seem.",
                  },
                  {
                    icon: <ShieldQuestion size={19} />,
                    title: "Make the call",
                    text: "Hire your pick. Then see what was hiding behind the résumé.",
                  },
                ].map((x, i) => (
                  <div className="how-step" key={x.title}>
                    <div className="how-icon">{x.icon}</div>
                    <div>
                      <span>0{i + 1}</span>
                      <h3>{x.title}</h3>
                      <p>{x.text}</p>
                    </div>
                  </div>
                ))}
                <div className="note">
                  <Sparkles size={17} />
                  <p>
                    Some candidates talk a big game.
                    <br />
                    <strong>Your job is to know the difference.</strong>
                  </p>
                </div>
              </aside>
            </div>
            <div className="bottom-note">
              <span>
                <CheckCheck size={16} /> No sign-up. No stakes. Just better
                instincts.
              </span>
              <span>
                Made for the curious interviewer{" "}
                <span className="tiny-star">✳</span>
              </span>
            </div>
          </>
        )}

        {screen === "summary" && job && (
          <>
            <section className="page-heading">
              <div className="eyebrow">THE INTERVIEW BRIEF</div>
              <h1>Let's get on the same page.</h1>
              <p>
                Fine-tune the role. We'll have your candidates ready in the
                wings.
              </p>
            </section>
            <section className="panel summary-panel">
              <div className="summary-fields">
                {(["title", "company", "seniority", "education"] as const).map(
                  (key) => (
                    <div key={key}>
                      <label htmlFor={key}>{key.toUpperCase()}</label>
                      <input
                        id={key}
                        value={job[key]}
                        onChange={(e) =>
                          setJob({ ...job, [key]: e.target.value })
                        }
                      />
                    </div>
                  ),
                )}
                <div className="full">
                  <label htmlFor="summary">THE BIG PICTURE</label>
                  <textarea
                    id="summary"
                    value={job.summary}
                    onChange={(e) =>
                      setJob({ ...job, summary: e.target.value })
                    }
                  />
                </div>
                {(["skills", "responsibilities"] as const).map((key) => (
                  <div key={key}>
                    <label htmlFor={key}>
                      {key.toUpperCase()} · ONE PER LINE
                    </label>
                    <textarea
                      id={key}
                      value={job[key].join("\n")}
                      onChange={(e) =>
                        setJob({ ...job, [key]: e.target.value.split("\n") })
                      }
                    />
                  </div>
                ))}
              </div>
              <div className="summary-bottom">
                <div>
                  <label>TIME PER CANDIDATE</label>
                  <div className="segmented">
                    <button
                      className={duration === 300 ? "selected" : ""}
                      onClick={() => setDuration(300)}
                    >
                      <Clock3 size={14} /> Full (5:00)
                    </button>
                    <button
                      className={duration === 90 ? "selected" : ""}
                      onClick={() => setDuration(90)}
                    >
                      Demo (1:30)
                    </button>
                  </div>
                </div>
                <div className="start-area">
                  <span>
                    {loadingCandidates
                      ? "Getting your candidates ready…"
                      : candidates.length
                        ? "3 candidates ready to meet you"
                        : "Candidates could not be loaded"}
                  </span>
                  {!candidates.length && !loadingCandidates && (
                    <button onClick={() => loadCandidates(job)}>
                      Retry candidates
                    </button>
                  )}
                  <button
                    className="primary"
                    disabled={
                      loadingCandidates ||
                      !candidates.length ||
                      !job.title.trim()
                    }
                    onClick={start}
                  >
                    Start interviews
                    <ArrowRight size={17} />
                  </button>
                </div>
              </div>
              <p className="small muted">
                Changes to the brief guide your interview questions. Candidate
                résumés are prepared from your original brief.
              </p>
            </section>
          </>
        )}

        {screen === "interview" && candidate && (
          <>
            <div className="interview-heading">
              <div>
                <div className="eyebrow">
                  {job?.title} · {job?.company || "YOUR TEAM"}
                </div>
                <h1>Look beyond the résumé.</h1>
              </div>
              <div className="interview-progress">
                <button
                  className="primary end-interview"
                  onClick={next}
                  title={`Next: rate ${candidate.name}${index === 2 ? ", then choose your hire" : ", then the next candidate"}`}
                >
                  End interview <ArrowRight size={16} />
                </button>
                <button
                  onClick={toggleMute}
                  aria-pressed={muted}
                  aria-label={
                    muted ? "Unmute candidate speech" : "Mute candidate speech"
                  }
                >
                  <AudioLines size={16} /> {muted ? "Unmute" : "Mute"}
                </button>
                <span>
                  Candidate {index + 1}/3 <b>·</b> Round {Math.min(round, 3)}/3
                </span>
                <strong className={seconds < 30 ? "urgent" : ""}>
                  <Clock3 size={17} />
                  {Math.floor(seconds / 60)}:
                  {String(seconds % 60).padStart(2, "0")}
                </strong>
              </div>
            </div>
            <div className="interview-grid">
              <aside className="panel candidate-panel">
                <Portrait
                  candidate={candidate}
                  prominent
                  talking={talking || delivering}
                />
                <h2>{candidate.name}</h2>
                <p className="muted">
                  Candidate 0{index + 1} · {job?.seniority}
                </p>
                <div className="resume-heading">
                  <FileText size={15} /> CANDIDATE RÉSUMÉ
                </div>
                <Resume candidate={candidate} />
              </aside>
              <section className="panel conversation">
                <div className="conversation-title">
                  <span className="status-dot" />
                  <strong>The conversation</strong>
                  <span>{entered ? "LIVE INTERVIEW" : "WAITING ROOM"}</span>
                </div>
                <div className="chat">
                  {!entered ? (
                    <div className="waiting">
                      <div className="waiting-icon">
                        <Users size={32} />
                      </div>
                      <h2>Your next candidate is here.</h2>
                      <p>
                        Read their résumé. Pick your opening question.
                        <br />
                        The timer starts when you bring them in.
                      </p>
                      <button
                        className="primary"
                        onClick={() => {
                          setEntered(true);
                          deliver(candidate.intro_line);
                          void speak(candidate.intro_line, candidate, index);
                        }}
                      >
                        Bring in {candidate.name.split(" ")[0]}
                        <ArrowRight size={17} />
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="bubble answer">
                        <label>{candidate.name}</label>
                        {candidate.intro_line}
                      </div>
                      {turns.map((t, i) => (
                        <div key={i}>
                          <div className="bubble question">
                            <label>YOU · {t.kind.toUpperCase()}</label>
                            {t.q}
                          </div>
                          <div className="bubble answer">
                            <label>{candidate.name}</label>
                            {t.a}
                          </div>
                        </div>
                      ))}
                      {pending && (
                        <>
                          <div className="bubble question">
                            <label>YOU</label>
                            {pending}
                          </div>
                          <div className="thinking">
                            <span /> {candidate.name.split(" ")[0]} is thinking…
                          </div>
                        </>
                      )}
                      <div ref={chatEnd} />
                    </>
                  )}
                </div>
                {entered && (
                  <div className="question-dock">
                    {round > 3 ? (
                      <div className="completed">
                        <CheckCheck size={22} />
                        <div>
                          <h3>That's a wrap.</h3>
                          <p>
                            Three rounds down. Trust the evidence, not just your
                            gut.
                          </p>
                        </div>
                        <button className="primary" onClick={next}>
                          {index === 2
                            ? "Make your decision"
                            : "Next candidate"}
                          <ArrowRight size={16} />
                        </button>
                      </div>
                    ) : (
                      <>
                        <label>
                          YOUR NEXT QUESTION{" "}
                          <span>CHOOSE ONE, OR MAKE IT YOUR OWN</span>
                        </label>
                        <div className="question-options">
                          {questions ? (
                            [
                              {
                                kind: "behavioural",
                                title: "Behavioural",
                                text: questions.behavioural,
                                tests: questions.behavioural_tests,
                              },
                              {
                                kind: "technical",
                                title: "Technical",
                                text: questions.technical,
                                tests: questions.technical_tests,
                              },
                              {
                                kind: questions.special.kind,
                                title:
                                  questions.special.kind === "resume"
                                    ? "Résumé"
                                    : "Follow-up",
                                text: questions.special.text,
                                tests: questions.special.tests,
                              },
                            ].map((q) => (
                              <button
                                key={q.kind}
                                disabled={busy || recording || transcribing}
                                onClick={() => ask(q.text, q.kind)}
                              >
                                <span>
                                  {q.title}
                                  <ArrowUpRight size={14} />
                                </span>
                                {q.text}
                                <small className="question-tests">
                                  {q.tests}
                                </small>
                              </button>
                            ))
                          ) : (
                            <p className="muted">
                              {questionError
                                ? "Suggestions unavailable. Ask your own question below."
                                : "Preparing question suggestions…"}
                            </p>
                          )}
                        </div>
                        <form
                          className="custom-question"
                          onSubmit={(e) => {
                            e.preventDefault();
                            void ask(custom, "custom");
                          }}
                        >
                          <input
                            aria-label="Ask your own question"
                            placeholder="Ask your own question…"
                            value={custom}
                            maxLength={4000}
                            onChange={(e) => setCustom(e.target.value)}
                            disabled={busy || recording || transcribing}
                          />
                          <span title={micTooltip}>
                            <button
                              type="button"
                              className={recording ? "recording" : ""}
                              disabled={!micAvailable || busy || transcribing}
                              aria-label="Hold to talk"
                              onPointerDown={(e) => {
                                e.currentTarget.setPointerCapture(e.pointerId);
                                void beginRecord();
                              }}
                              onPointerUp={endRecord}
                              onPointerCancel={endRecord}
                              onKeyDown={(e) => {
                                if (e.key === " " && !e.repeat) {
                                  e.preventDefault();
                                  void beginRecord();
                                }
                              }}
                              onKeyUp={(e) => {
                                if (e.key === " ") endRecord();
                              }}
                            >
                              <Mic size={18} />
                            </button>
                          </span>
                          <button
                            type="submit"
                            disabled={
                              busy ||
                              recording ||
                              transcribing ||
                              !custom.trim()
                            }
                            aria-label="Send question"
                          >
                            <Send size={18} />
                          </button>
                        </form>
                        {notice && (
                          <p className="small muted" role="status">
                            {notice}
                          </p>
                        )}
                        <div className="dock-footer">
                          <span>
                            {recording
                              ? "Recording… release to transcribe"
                              : transcribing
                                ? "Transcribing…"
                                : "3 rounds. Make each question count."}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </section>
            </div>
          </>
        )}

        {screen === "rating" && candidate && (
          <section className="panel rating-panel">
            <div className="eyebrow">
              TRUST YOUR READ · CANDIDATE {index + 1}/3
            </div>
            <Portrait candidate={candidate} />
            <h1>How did {candidate.name.split(" ")[0]} come across?</h1>
            <p>
              Rate before the reveal. Later, compare your instincts with the
              simulation's hidden profile.
            </p>
            {Object.entries(ratingLabels).map(([key, label]) => (
              <fieldset key={key}>
                <legend>{label}</legend>
                <div className="rating-options">
                  {[1, 2, 3, 4, 5].map((value) => (
                    <button
                      key={value}
                      aria-label={`${label}: ${value}`}
                      aria-pressed={
                        (ratings[candidate.id] || defaultRating)[
                          key as keyof Rating
                        ] === value
                      }
                      className={
                        (ratings[candidate.id] || defaultRating)[
                          key as keyof Rating
                        ] === value
                          ? "selected"
                          : ""
                      }
                      onClick={() =>
                        setRatings((r) => ({
                          ...r,
                          [candidate.id]: {
                            ...(r[candidate.id] || defaultRating),
                            [key]: value,
                          },
                        }))
                      }
                    >
                      {value}
                    </button>
                  ))}
                </div>
              </fieldset>
            ))}
            <p className="small muted">
              1 = low · 3 = mixed · 5 = strong. Defaults are 3 until changed.
            </p>
            <button
              className="primary"
              onClick={() => {
                setRatings((r) => ({
                  ...r,
                  [candidate.id]: r[candidate.id] || defaultRating,
                }));
                if (index === 2) setScreen("hire");
                else {
                  setIndex((i) => i + 1);
                  setScreen("interview");
                }
              }}
            >
              {index === 2 ? "Choose your hire" : "Next candidate"}
              <ArrowRight size={16} />
            </button>
          </section>
        )}

        {screen === "hire" && (
          <>
            <section className="page-heading">
              <div className="eyebrow">THE DECISION</div>
              <h1>One role. Three stories. Your call.</h1>
              <p>
                Take a last look at the evidence. Who would you want on your
                team?
              </p>
            </section>
            <div className="hire-grid">
              {candidates.map((c) => (
                <section key={c.id} className="panel hire-card">
                  <Portrait candidate={c} />
                  <h2>{c.name}</h2>
                  <Resume candidate={c} compact />
                  <div className="recap">
                    <label>FROM YOUR CONVERSATION</label>
                    {(transcripts[c.id] || []).length ? (
                      <>
                        <p>“{transcripts[c.id].at(-1)?.a}”</p>
                        <details>
                          <summary>
                            Read all {transcripts[c.id].length} rounds
                          </summary>
                          {transcripts[c.id].map((t, j) => (
                            <div key={j}>
                              <strong>{t.q}</strong>
                              <p>{t.a}</p>
                            </div>
                          ))}
                        </details>
                      </>
                    ) : (
                      <p>You didn't interview this candidate.</p>
                    )}
                  </div>
                  <button
                    className="primary wide"
                    disabled={busy}
                    onClick={() => hire(c.id)}
                  >
                    {busy && hired === c.id
                      ? "Reviewing your decision…"
                      : `Hire ${c.name.split(" ")[0]}`}
                    <ArrowRight size={16} />
                  </button>
                </section>
              ))}
            </div>
          </>
        )}

        {screen === "feedback" && evaluation && (
          <>
            <section className="page-heading">
              <div className="eyebrow">YOUR PERSONAL INTERVIEW PLAYBOOK</div>
              <h1>What to do in YOUR interviews</h1>
              <p>
                Borrow the strongest signals. Leave the empty claims behind.
              </p>
            </section>
            <div className="lesson-grid">
              {[
                {
                  title: "Do · make your contribution clear",
                  lessons: evaluation.dos,
                  tone: "good",
                },
                {
                  title: "Don't · let polish replace proof",
                  lessons: evaluation.donts,
                  tone: "bad",
                },
              ].map((group) => (
                <section
                  className={"panel lessons " + group.tone}
                  key={group.title}
                >
                  <h2>{group.title}</h2>
                  {group.lessons.length ? (
                    group.lessons.map((lesson, i) => (
                      <article key={i}>
                        <h3>
                          {i + 1}. {lesson.advice}
                        </h3>
                        <blockquote>“{lesson.quote}”</blockquote>
                        <p className="small muted">
                          {
                            candidates.find((c) => c.id === lesson.candidate_id)
                              ?.name
                          }{" "}
                          · exact answer excerpt
                        </p>
                      </article>
                    ))
                  ) : (
                    <p>
                      No answers from this candidate yet. Interview them next
                      time to unlock evidence-backed lessons.
                    </p>
                  )}
                </section>
              ))}
            </div>
            <div className="section-label">
              <h2>Behind the résumé</h2>
              <span>
                The attributes you couldn't see. The signals you could.
              </span>
            </div>
            <div className="reveal-grid">
              {candidates.map((c, i) => {
                const summary = evaluation.candidate_summaries.find(
                  (s) => s.id === c.id,
                );
                return (
                  <section className="panel reveal-card" key={c.id}>
                    <div className="reveal-name">
                      <Portrait candidate={c} />
                      <div>
                        <h3>{c.name}</h3>
                        <span className="muted small">
                          {c.id === evaluation.best_fit_id
                            ? "✦ BEST FIT"
                            : c.id === hired
                              ? "YOUR HIRE"
                              : "CANDIDATE 0" + (i + 1)}
                        </span>
                      </div>
                    </div>
                    <h3>{c.archetype}</h3>
                    <p>{c.archetype_blurb}</p>
                    <p>{summary?.summary}</p>
                    <div className="attributes">
                      {Object.entries(c.attributes).map(([key, value]) => (
                        <div key={key}>
                          <label>
                            {key === "larping" ? "Larping / bluffing" : key}
                            <span>{value}/10</span>
                          </label>
                          <div
                            className={
                              "bar " + (key === "larping" ? "bluff" : "")
                            }
                          >
                            <span style={{ width: `${value * 10}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                    <label>THE INFLATED CLAIMS</label>
                    {c.fabricated_claims.map((claim) => (
                      <p className="claim" key={claim}>
                        {claim}
                      </p>
                    ))}
                    <div className="bluff-report">
                      <strong>Bluffs caught</strong>
                      <p>
                        {summary?.bluffs_caught.join(" · ") ||
                          "None identified."}
                      </p>
                      <strong>Bluffs missed</strong>
                      <p>
                        {summary?.bluffs_missed.join(" · ") ||
                          "No remaining claims flagged."}
                      </p>
                    </div>
                  </section>
                );
              })}
            </div>
            <section className="panel rating-comparison">
              <h2>How accurate was your read?</h2>
              <p>
                Fictional profile benchmarks, not measurements of real people.
                Gaps of 2 or more are flagged.
              </p>
              {evaluation.rating_comparisons.map((r) => (
                <article key={r.id}>
                  <h3>{candidates.find((c) => c.id === r.id)?.name}</h3>
                  <div className="rating-table">
                    {Object.entries(ratingLabels).map(([key, label]) => (
                      <p key={key}>
                        <strong>{label}</strong>
                        <span>
                          You: {r.user?.[key as keyof Rating] ?? "Not rated"} ·
                          Profile: {r.truth[key as keyof Rating]}/5
                        </span>
                      </p>
                    ))}
                  </div>
                  {r.flags.map((flag) => (
                    <p className="rating-flag" key={flag}>
                      {flag}
                    </p>
                  ))}
                  {!r.flags.length && (
                    <p className="muted">
                      {r.user
                        ? "Your read was within one point on every dimension."
                        : "No rating submitted."}
                    </p>
                  )}
                </article>
              ))}
            </section>
            <section className="panel annotated-replay">
              <h2>Annotated replay · see what interviewers notice</h2>
              {candidates.map((c) => (
                <article key={c.id}>
                  <h3>
                    {c.name} · {c.archetype}
                  </h3>
                  {(transcripts[c.id] || []).length ? (
                    transcripts[c.id].map((turn, i) => {
                      const note = evaluation.annotations[c.id]?.[i];
                      return (
                        <div
                          key={i}
                          className={"replay-turn " + (note?.tone || "neutral")}
                        >
                          <strong>{turn.q}</strong>
                          <p>{turn.a}</p>
                          {note && (
                            <aside>
                              <b>{note.label}</b> ·{" "}
                              {note.why_interviewers_notice}
                            </aside>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <p>No answers recorded.</p>
                  )}
                </article>
              ))}
            </section>
            <section className="panel hire-result">
              <h2>Your hiring decision · {evaluation.interviewer_score}/100</h2>
              <p>
                You hired {candidates.find((c) => c.id === hired)?.name}. Best
                fit:{" "}
                {candidates.find((c) => c.id === evaluation.best_fit_id)?.name}.
              </p>
              <p>{evaluation.verdict}</p>
              <small>
                The hiring score is secondary. Take your lessons into your next
                real interview.
              </small>
            </section>
            <div className="feedback-grid">
              <section className="panel">
                <h2>Your question game</h2>
                <label>STRONG SIGNALS</label>
                {evaluation.best_questions.length ? (
                  evaluation.best_questions.map((q, i) => (
                    <div className="review-question" key={i}>
                      <Check size={17} />
                      <div>
                        <strong>{q.text}</strong>
                        <p>{q.why}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p>
                    No evidence-seeking questions yet. Try a specific résumé
                    probe next time.
                  </p>
                )}
                <label>ROOM TO DIG DEEPER</label>
                {evaluation.weak_questions.map((q, i) => (
                  <div className="review-question" key={i}>
                    <ArrowUpRight size={17} />
                    <div>
                      <strong>{q.text}</strong>
                      <p>{q.why}</p>
                    </div>
                  </div>
                ))}
              </section>
              <section className="panel tips">
                <Sparkles size={22} />
                <h2>Take this into your next interview.</h2>
                {evaluation.tips.map((tip, i) => (
                  <div key={tip}>
                    <span>0{i + 1}</span>
                    <p>{tip}</p>
                  </div>
                ))}
                <p className="small muted">
                  Best fit is deterministic: role-weighted ability, mood and
                  charisma, minus a bluffing penalty. This is practice, not a
                  real hiring assessment.
                </p>
              </section>
            </div>
            <div className="replay">
              <div>
                <h2>Think you can read the room now?</h2>
                <p>Same role, a fresh cast. Put your instincts to the test.</p>
              </div>
              <button
                disabled={loadingCandidates}
                className="primary"
                onClick={async () => {
                  if (!job) return;
                  setScreen("summary");
                  await loadCandidates(job);
                }}
              >
                <RotateCcw size={16} />
                Try again
              </button>
              <button
                onClick={() => {
                  stopAudio();
                  setScreen("input");
                  setJd("");
                  setShowPresets(false);
                  setError("");
                }}
              >
                New job
                <ArrowUpRight size={16} />
              </button>
            </div>
          </>
        )}
      </main>
      <footer>
        <span>InterviewLARP</span>
        <span>Fictional candidates. Real interviewing practice.</span>
        <span>Stay curious. Ask one more question.</span>
      </footer>
    </>
  );
}
