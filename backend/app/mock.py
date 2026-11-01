import random
import uuid

from .models import Candidate, Evaluation, Job, Questions, Rating, RatingComparison
from .archetypes import ARCHETYPES, select_archetypes


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


def mock_candidates(job: Job, archetypes=None) -> list[Candidate]:
    names = random.sample(["Alex Morgan", "Jamie Chen", "Sam Rivera", "Taylor Brooks", "Robin Patel", "Jordan Ellis", "Casey Park", "Avery Quinn", "Morgan Reed"], 3)
    selected = select_archetypes() if archetypes is None else archetypes
    result = []
    for i, archetype in enumerate(selected):
        profile = ARCHETYPES[archetype]
        mood, smartness, charisma, larping = profile["profile"]
        claim = f"Led a small team project using {job.skills[0]}"
        claims = [claim, "Helped the team finish tasks 20% faster"] if larping > 7 else ["Sole owner of the team's onboarding playbook"]
        result.append(Candidate.model_validate({
            "id": str(uuid.uuid4()), "name": names[i], "voice_id": VOICES[i],
            "archetype": archetype, "archetype_blurb": profile["blurb"],
            "intro_line": f"Hi, I'm {names[i].split()[0]}. Thanks for making time. I'd love to tell you about my work and learn more about {job.company or 'your team'}.",
            "attributes": dict(mood=mood, smartness=smartness, charisma=charisma, larping=larping),
            "resume": {"education": "Community college · practical training and independent projects", "experience": ["Project contributor · Fieldwork Studio · 2023–2025", *claims], "skills": job.skills + ["Team collaboration"], "projects": [f"Built a practical {job.skills[0]} workflow", "Organized a peer learning workshop"]},
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
    question = req.question.lower()
    kind = req.kind
    if kind == 'custom':
        if any(w in question for w in ['you said', 'specifically', 'evidence']):
            kind = 'followup'
        elif any(w in question for w in ['resume', 'résumé', 'exact contribution', 'claim']):
            kind = 'resume'
        elif any(w in question for w in ['approach', 'trade-off', 'what could', 'teach', 'debug']):
            kind = 'technical'
        elif any(w in question for w in ['time you', 'disagreement', 'deadline', 'mistake']):
            kind = 'behavioural'
    skill = req.job.skills[0] if req.job.skills else 'the work'
    round_index = min(len(req.transcript), 2)
    archetype = req.candidate.archetype
    if archetype == "The Idiot":
        answers = {
            'behavioural': "I'm not sure I have an example. I usually waited for someone to tell me which task to do.",
            'technical': f"I'm not really sure how to start a {skill} task. Do you mean opening the example first?",
            'resume': "I put that on there because I attended the project meetings. I can't really explain how the work was done.",
            'followup': "Sorry, I don't know which part you mean. I didn't keep track of what changed.",
            'custom': "I haven't thought about that before. Could you explain what you're asking?",
        }
        endings = ["I would need some guidance.", "I haven't practised that yet.", "I don't have much more to add."]
    elif archetype == "The Cocky One":
        technical = "Python lists can't be changed once you create them, so there's no need to check for accidental changes." if 'python' in skill.lower() else f"For {skill}, a successful first attempt proves the process will always work. Testing other cases is a waste of time."
        answers = {
            'behavioural': "My teammate wanted another review, but I knew my version was right. We missed a requirement, though I still think checking it again would have slowed us down.",
            'technical': technical,
            'resume': "I was obviously the main reason the project worked. If the team finished 20% faster, that proves every task took exactly 20% less time.",
            'followup': "There's no need to look at the failed cases. If one example passed, that proves the approach is correct for every input.",
            'custom': "I pick this stuff up faster than most people. Feedback isn't really necessary once you've understood the idea the first time.",
        }
        endings = ["I'm pretty certain about that.", "I don't see why we'd need another opinion.", "I'd stick with my answer."]
    elif archetype == "The Casual One":
        answers = {
            'behavioural': "Tbh, I messed up a handover and my teammate was lowkey annoyed. I apologised and wrote a checklist so we both knew what was left.",
            'technical': f"For {skill}, I'd try, like, one normal example and one awkward case first. I recorded the results and asked a teammate to check the bit I wasn't sure about.",
            'resume': "Yeah, 'sole owner' is a bit much, tbh. I wrote the checklist, but my teammate drafted the rest and reviewed my changes.",
            'followup': "Like, my actual part was tracking the failures and fixing the unclear instructions. Lowkey the useful bit was asking two people to try it before we called it done.",
            'custom': "Tbh, I learn best by trying a small task and asking questions when I get stuck. I keep notes so I don't make the same mistake next time.",
        }
        endings = ["That helped us out, honestly.", "I'd keep doing the checks, for sure.", "That's the main takeaway for me, tbh."]
    elif archetype == "The Rambler":
        answers = {
            'behavioural': "We disagreed about the task order, which reminds me that we'd just moved our meeting to Tuesday because of someone's class. Anyway, I asked everyone to list their blockers and we picked one task to finish together.",
            'technical': f"For {skill}, there are a few things I'd try, and I first heard about one of them in a workshop with a really long signup process. The relevant part is that I'd test a small example and record what failed.",
            'resume': "The playbook started with a chat after a meeting, and we actually spent ages choosing where to save it. My part was writing the setup steps and asking a newcomer to try them.",
            'followup': "I took notes, and I also sorted out the shared folder, which had a confusing name from an older project. To answer your question, I recorded two failed checks and fixed one unclear step.",
            'custom': "There are lots of ways I could answer that, including a workshop where we spent most of the morning setting up. The useful thing I learned was to ask for feedback on a small first attempt.",
        }
        endings = ["There was another detail, but that's probably the main point.", "I suppose I could have started with that part.", "Anyway, that's what I was getting at."]
    elif archetype == "The Under-seller":
        answers = {
            'behavioural': "It was just a small thing, but I noticed we kept missing handovers. I made a checklist and checked it with two teammates; we stopped missing those steps.",
            'technical': f"I'm not an expert at {skill}, but I wrote a small check for the usual case and the failure case. It caught a problem before we shared the work, though it wasn't anything impressive.",
            'resume': "I wasn't really the owner of the playbook. I only wrote the setup steps and tested them with two new starters, who both finished without needing help.",
            'followup': "I just compared the failed checks before and after my change. They all passed afterwards, but I don't want to make too much of a small fix.",
            'custom': "I don't have a huge achievement to talk about. I helped a teammate understand a tricky step by writing a worked example, and they used it successfully the next day.",
        }
        endings = ["It was a useful little contribution, I guess.", "I probably should explain what changed more clearly.", "I did do that part myself."]
    elif archetype == "The Smooth Bluffer":
        answers = {
            'behavioural': "When we were behind on a group project, I helped everyone agree on what to finish first. We got most of it done by the deadline, though I didn't really track which changes made the difference.",
            'technical': f"For {skill}, I'd probably start with a similar example and adapt it to what we need. That worked on our project, although a teammate handled most of the testing, so I'm not sure how they checked it.",
            'resume': "I helped organise the tasks and kept the group updated. The improvement was roughly what we noticed at the time; I don't have a clear before-and-after measurement.",
            'followup': "I put together the progress update and helped with the presentation. I wasn't the one doing that part of the implementation, so I'd need to check with my teammate about the exact steps.",
            'custom': "I'm usually comfortable getting a group started and explaining our work. I can give you the general approach, but I'd need to look back at my notes for the details of my part.",
        }
        endings = ["I think the team worked pretty well together.", "I'd probably check that more carefully next time.", "That's about as much as I can remember without the project notes."]
    elif archetype == "The Nervous Genius":
        answers = {
            'behavioural': "Um, I missed a handover because I assumed a teammate had seen my notes. I owned the mistake, apologised, and made a checklist with them so each handover had a named reviewer.",
            'technical': f"For {skill}, I'd define a small success criterion, then test the simplest approach against a normal case and an edge case. My first attempt failed under peak load, so I reduced the scope, retested and recorded the trade-off.",
            'resume': "Oh, I wasn't the sole owner of the onboarding playbook — a colleague wrote the first draft. I added the checklist and tested it with two newcomers; one unclear step led me to rewrite the instructions.",
            'followup': "Specifically, I wrote the checklist, ran the comparison and recorded which cases failed before and after the change. Um, the sample was small, so I asked for help checking whether the result would generalise.",
            'custom': "Um, I sometimes take a moment to organise my thoughts. In a peer workshop, I asked for help explaining an unfamiliar topic, then used a worked example to check what the group understood.",
        }
        endings = ["I get nervous describing it, but I can explain my own steps.", "The useful lesson for me was to make the checks reproducible.", "I would rather be precise about a limitation than promise more than I know."]
    else:
        answers = {
            'behavioural': "When a teammate disagreed with my plan, I asked what risk they were seeing. We tried both options on a small task, then documented what worked and agreed on the next step together.",
            'technical': f"For a difficult {skill} task, I'd clarify the requirements, try a small example and ask a teammate to review it. I kept a checklist of expected results so we could spot problems before expanding the work.",
            'resume': "Calling the onboarding playbook solely mine was overstating it. I interviewed two new starters, drafted the troubleshooting checklist and had the original author review my changes.",
            'followup': "What I owned was the first draft and the review meeting, not the whole project. I documented what worked after two colleagues tried it, and changed the step they both found confusing.",
            'custom': "I prepare by choosing a concrete example and separating my role from the team's result. When I lacked experience with a task, I asked for help early and documented what worked for the next person.",
        }
        endings = ["I try to make my contribution easy to follow.", "That experience taught me to check assumptions with other people.", "Next time I would agree on the success measure before starting."]
    return {"answer": answers[kind] + ' ' + endings[round_index]}


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
            if c.archetype == "The Casual One":
                tone, label, why = "neutral", "Casual tone, useful substance", "Informal language can feel relatable and authentic, but too much slang can sound unprofessional. Look for the concrete action underneath."
            elif c.archetype == "The Cocky One":
                tone, label, why = "bad", "Overconfidence without checking", "Certainty is not evidence: dismissing checks and stating incorrect assumptions makes errors harder to catch."
            elif c.archetype == "The Idiot":
                tone, label, why = "bad", "Missing fundamentals", "This answer does not show how to approach the work. Ask for clarification and prepare a small relevant example."
            elif c.archetype == "The Rambler":
                tone, label, why = "neutral", "Buried the point", "Useful actions are harder to notice when side stories come before the answer."
            elif c.archetype == "The Under-seller":
                tone, label, why = "good", "Understated contribution", "A small, concrete action still counts as evidence. Explain its impact without dismissing your work."
            elif c.archetype == "The Smooth Bluffer":
                tone, label, why = "bad", "Thin evidence", "Polished delivery needs a specific personal action and a checkable result."
            elif "80%" in text and "don't have" not in text:
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
    advice = ARCHETYPES.get(ordered[0].archetype, {}).get("advice", "Explain your own actions and gaps honestly.")
    donts = lessons(ordered[0], [advice, "Don't substitute confidence for a checked explanation.", "Don't hide your contribution or gaps: give a concrete example."])
    return {"annotations": annotations, "dos": dos, "donts": donts, "rating_comparisons": rating_comparisons(req)}


def mock_evaluation(req) -> Evaluation:
    best = best_fit(req.job, req.candidates)
    turns = [t for ts in req.transcripts.values() for t in ts]
    strong = [t for t in turns if t.kind in ["resume", "followup"] or any(w in t.q.lower() for w in ["evidence", "specifically", "measured", "exact"])]
    weak = [t for t in turns if t not in strong]
    summaries = []
    for c in req.candidates:
        probed = any(t in strong for t in req.transcripts.get(c.id, []))
        profile = ARCHETYPES.get(c.archetype, {})
        summaries.append({"id": c.id, "summary": profile.get("blurb", c.archetype_blurb) + " " + profile.get("advice", "Ask for evidence of personal contribution."), "bluffs_caught": c.fabricated_claims if probed else [], "bluffs_missed": [] if probed else c.fabricated_claims})
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
