import random
import uuid

from .models import Candidate, Evaluation, Job, Questions, Rating, RatingComparison


PRESETS = [
    Job(title="Software Engineering Intern", company="Orbit", seniority="Intern", education="CS student or equivalent projects", skills=["Python", "Problem solving", "Testing"], responsibilities=["Ship small features", "Debug with a mentor", "Write tests"], summary="Build thoughtful software on a small, supportive product team."),
    Job(title="Barista", company="Sunday Coffee", seniority="Entry level", education="No formal requirement", skills=["Customer service", "Espresso", "Teamwork"], responsibilities=["Prepare drinks", "Handle rush-hour orders", "Keep the bar clean"], summary="Make great coffee and make people feel at home, even during the morning rush."),
    Job(title="Product Manager", company="Northstar", seniority="Mid-level", education="Equivalent professional experience", skills=["Prioritization", "Analytics", "Communication"], responsibilities=["Define product outcomes", "Talk to customers", "Align stakeholders"], summary="Turn ambiguous customer problems into focused, measurable product bets."),
    Job(title="Community Manager", company="Common Ground", seniority="Associate", education="Equivalent experience", skills=["Communication", "Moderation", "Events"], responsibilities=["Welcome new members", "Resolve conflict", "Run community events"], summary="Build a welcoming community with consistent, empathetic communication."),
]

VOICES = ["JBFqnCBsd6RMkjVDRZzb", "EXAVITQu4vr4xnSDxMaL", "pNInz6obpgDQGcFmaJgB"]


def mock_job(text: str) -> Job:
    lower = text.lower()
    job = next((j for j in PRESETS if any(s.lower() in lower for s in [j.title, *j.skills])), PRESETS[0])
    return job.model_copy(update={"summary": "Practice role based on your description: " + text.strip()[:260]})


def mock_candidates(job: Job) -> list[Candidate]:
    names = random.sample(["Alex Morgan", "Jamie Chen", "Sam Rivera", "Taylor Brooks", "Robin Patel", "Jordan Ellis", "Casey Park", "Avery Quinn", "Morgan Reed"], 3)
    profiles = [(6, 3, 10, 9), (4, 9, 5, 2), (9, 7, 8, 4)]
    random.shuffle(profiles)
    result = []
    for i, (mood, smartness, charisma, larping) in enumerate(profiles):
        claim = f"Led a team of 12 delivering a company-wide {job.skills[0]} initiative"
        claims = [claim, "Improved team performance by 80% in one month"] if larping > 7 else ["Sole owner of the team's onboarding playbook"]
        archetype, blurb = ("The Smooth Bluffer", "Confident headlines hide missing evidence.") if larping > 7 else ("The Nervous Genius", "Quiet delivery, careful reasoning; nerves are not lack of ability.") if smartness > 8 else ("The Prepared One", "Warm, structured examples make their contribution easy to follow.")
        result.append(Candidate.model_validate({
            "id": str(uuid.uuid4()), "name": names[i], "voice_id": VOICES[i],
            "archetype": archetype, "archetype_blurb": blurb,
            "intro_line": f"Hi, I'm {names[i].split()[0]}. Thanks for making time. I'd love to tell you about my work and learn more about {job.company or 'your team'}.",
            "attributes": dict(mood=mood, smartness=smartness, charisma=charisma, larping=larping),
            "resume": {"education": "Distinction, advanced professional diploma" if larping > 7 else "Community college · practical training and independent projects", "experience": [f"{'Senior lead' if larping > 7 else 'Team contributor'} · Fieldwork Studio · 2023–2025", *claims], "skills": job.skills + ["Team collaboration"], "projects": [f"Built a practical {job.skills[0]} workflow", "Organized a peer learning workshop"]},
            "fabricated_claims": claims,
        }))
    return result


def mock_questions(req) -> Questions:
    skill = req.job.skills[0] if req.job.skills else "your core skill"
    behaviour = ["Tell me about a time you made a mistake. What changed afterward?", "Describe a disagreement with a teammate. What did you actually do?", "When a deadline slipped, how did you communicate it?"][req.round - 1]
    technical = [f"Walk me through how you would approach a difficult {skill} task. How would you check your work?", f"What could go wrong with that {skill} approach, and how would you detect it?", f"Teach a beginner one important {skill} trade-off using a concrete example."][req.round - 1]
    if req.round > 1 and req.transcript:
        special = {"kind": "followup", "text": f'You said “{req.transcript[-1].a[:100]}…”. What specifically did YOU do, and what evidence shows it worked?'}
    else:
        special = {"kind": "resume", "text": f'Your resume says “{req.candidate.resume.experience[-1]}”. Walk me through your exact contribution and how the result was measured.'}
    special["tests"] = "Tests whether the résumé claim is real" if special["kind"] == "resume" else "Tests evidence and personal ownership"
    return Questions(behavioural=behaviour, technical=technical, behavioural_tests="Tests ownership and reflection", technical_tests="Tests reasoning and how they check their work", special=special)


def mock_answer(req) -> dict:
    a = req.candidate.attributes
    probe = any(w in req.question.lower() for w in ["specifically", "exact", "evidence", "measured", "resume", "trade-off", "what could"])
    if a.larping > 7:
        answer = ("Right, so I should clarify: I was more involved in coordinating the updates than doing the implementation. I don't have the raw numbers; the 80% figure came from a slide someone shared. I can't walk through the underlying method without checking with the team." if probe else "Absolutely — I led that end to end and transformed how the whole team operated. We improved performance by 80% through a highly scalable, best-in-class approach. My biggest strength is making ambitious things happen at speed.")
    elif a.smartness > 8:
        skill = req.job.skills[0] if req.job.skills else "the work"
        answer = f"Um, I'd start by defining what success means for {skill} and trying a small, observable version first. In my project I kept a checklist, compared before-and-after results, and asked a teammate to review the edge cases. The first attempt failed under peak load, so I reduced the scope and retested. I wasn't the sole owner of onboarding, though — a colleague wrote the initial draft."
    else:
        answer = "I try to understand who is affected before jumping to a solution. Last time, I asked a teammate to work through a small test with me, then documented what worked and what didn't. I helped improve our onboarding playbook, although calling it solely mine would be overstating it. I'd bring that same collaborative approach here."
    return {"answer": answer}


def fit_score(job: Job, candidate: Candidate) -> float:
    a = candidate.attributes
    people_facing = any(w in job.title.lower() for w in ["barista", "community", "sales", "customer"])
    weights = (0.25, 0.30, 0.45) if people_facing else (0.60, 0.20, 0.20)
    return a.smartness * weights[0] + a.mood * weights[1] + a.charisma * weights[2] - a.larping * 0.35


def best_fit(job: Job, candidates: list[Candidate]) -> str:
    if not candidates:
        raise ValueError("At least one candidate is required")
    return max(candidates, key=lambda c: (fit_score(job, c), c.id)).id


def rating_comparisons(req):
    comparisons = []
    for c in req.candidates:
        a = c.attributes
        scale = lambda value: max(1, min(5, round(value / 2)))
        truth = Rating(communication=scale(a.charisma), evidence=scale(a.smartness), honesty=scale(11 - a.larping), job_fit=max(1, min(5, round(fit_score(req.job, c)))))
        user = req.ratings.get(c.id)
        flags = [f"{key.replace('_', ' ').title()}: you rated {getattr(user, key)}/5; the simulation benchmark is {value}/5. Separate confident delivery from demonstrated ability." for key, value in truth.model_dump().items() if user and abs(getattr(user, key) - value) >= 2]
        comparisons.append(RatingComparison(id=c.id, truth=truth, user=user, flags=flags))
    return comparisons


def learning_content(req):
    annotations = {}
    for c in req.candidates:
        annotations[c.id] = []
        for t in req.transcripts.get(c.id, []):
            text = t.a.lower()
            if "80%" in text and "don't have" not in text:
                tone, label, why = "bad", "Bluffing", "A big number without a method or personal contribution is hard to trust."
            elif "don't have" in text or "can't walk" in text:
                tone, label, why = "bad", "Unsupported claim", "The follow-up reveals that the original claim lacks first-hand evidence."
            elif "first attempt failed" in text or "checklist" in text:
                tone, label, why = "good", "Specific example", "Concrete actions, checks and a failure show how the candidate thinks."
            elif "asked for help" in text or "what i owned" in text or "documented what worked" in text:
                tone, label, why = "good", "Ownership and reflection", "Naming your own actions and learning makes your contribution credible."
            else:
                tone, label, why = "neutral", "Needs a follow-up", "Listen for a concrete action and outcome before drawing conclusions."
            annotations[c.id].append({"tone": tone, "label": label, "why_interviewers_notice": why})
    ordered = sorted(req.candidates, key=lambda c: fit_score(req.job, c))
    def lessons(c, advice):
        ts = req.transcripts.get(c.id, [])
        return [{"candidate_id": c.id, "quote": ts[i % len(ts)].a, "advice": tip} for i, tip in enumerate(advice)] if ts else []
    dos = lessons(ordered[-1], ["Explain your own actions, not just the team's headline.", "Describe how you checked your work and what changed.", "Use a concrete example; thoughtful pauses are fine."])
    donts = lessons(ordered[0], ["Don't lead with an impressive number you cannot substantiate.", "Don't substitute confident buzzwords for your actual contribution.", "Don't inflate ownership: explain your real role and gaps early."])
    return {"annotations": annotations, "dos": dos, "donts": donts, "rating_comparisons": rating_comparisons(req)}


def mock_evaluation(req) -> Evaluation:
    best = best_fit(req.job, req.candidates)
    turns = [t for ts in req.transcripts.values() for t in ts]
    strong = [t for t in turns if t.kind in ["resume", "followup"] or any(w in t.q.lower() for w in ["evidence", "specifically", "measured", "exact"])]
    weak = [t for t in turns if t not in strong]
    summaries = []
    for c in req.candidates:
        probed = any(t in strong for t in req.transcripts.get(c.id, []))
        summaries.append({"id": c.id, "summary": "Polished delivery masked thin hands-on experience." if c.attributes.larping > 7 else "Practical ability showed through; distinguish quiet confidence from lack of skill." if c.attributes.smartness > 8 else "A warm, capable collaborator with some inflated ownership claims.", "bluffs_caught": c.fabricated_claims if probed else [], "bluffs_missed": [] if probed else c.fabricated_claims})
    coverage = []
    for c in req.candidates:
        candidate_turns = req.transcripts.get(c.id, [])[:3]
        kinds = {t.kind for t in candidate_turns if t.kind in ["behavioural", "technical"]}
        if any(t in strong for t in candidate_turns):
            kinds.add("probe")
        coverage.append(kinds)
    coverage_score = 6 * sum(len(kinds) for kinds in coverage)
    comparable_score = 8 * sum(all(kind in kinds for kinds in coverage) for kind in ["behavioural", "technical"])
    score = max(1, coverage_score + comparable_score + (30 if req.hired_id == best else 0))
    if req.hired_id != best:
        score = min(score, 70)
    return Evaluation(**learning_content(req), best_fit_id=best, hired_was_best=req.hired_id == best, interviewer_score=score, verdict="You hired for substance, not just the story." if req.hired_id == best else "The strongest story wasn't the strongest signal. Look for evidence, not polish.", candidate_summaries=summaries, best_questions=[{"text": t.q, "why": "Asked for specific ownership or evidence rather than accepting the headline."} for t in strong[:3]], weak_questions=[{"text": t.q, "why": "A useful opener, but follow it with a concrete example and measurable result."} for t in weak[:2]], tips=["Ask every candidate one comparable job-relevant question.", "Probe ownership: what did you personally do, and what would you change?", "Don't mistake nervousness for lack of ability. Mock feedback uses question-type heuristics, not a semantic truth detector."])
