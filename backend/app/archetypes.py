import random


ARCHETYPES = {
    "The Prepared One": {
        "profile": (9, 7, 8, 4),
        "blurb": "Warm, structured examples make their contribution easy to follow.",
        "style": "Use clear, concise examples with personal actions, checks and reflection.",
        "advice": "Keep your examples specific and separate your own work from the team's result.",
    },
    "The Nervous Genius": {
        "profile": (4, 9, 5, 2),
        "blurb": "Quiet delivery, careful reasoning; nerves are not lack of ability.",
        "style": "Hesitate occasionally, but give careful reasoning and acknowledge limitations. No constant ums or panic.",
        "advice": "Take a breath, then explain your reasoning; a thoughtful pause is better than rushing.",
    },
    "The Smooth Bluffer": {
        "profile": (6, 3, 10, 9),
        "blurb": "Confident headlines hide missing first-hand evidence.",
        "style": "Sound polished but vaguely confident. Overstate small contributions and struggle to provide specifics. No grandiose achievements.",
        "advice": "Replace polished generalities with evidence and be honest about what you do not know.",
    },
    "The Rambler": {
        "profile": (7, 6, 6, 3),
        "blurb": "Has useful experience, but side stories bury the answer.",
        "style": "Wander through a realistic side detail before eventually giving a relevant point. Keep within 2-5 sentences.",
        "advice": "Lead with your answer, add one relevant example, then stop rather than adding side stories.",
    },
    "The Under-seller": {
        "profile": (5, 8, 4, 1),
        "blurb": "Capable and honest, but downplays meaningful personal contributions.",
        "style": "Understate your useful work with phrases like 'just a small change', while revealing concrete competence when probed.",
        "advice": "Name what you actually did and its impact without dismissing it as 'just' a small task.",
    },
    "The Idiot": {
        "profile": (4, 2, 3, 2),
        "blurb": "Unprepared and genuinely unsure how to approach the work; confusion is not a joke.",
        "style": "Be genuinely lost: short, confused or slightly off-topic answers with little practical understanding. Admit uncertainty. Stay realistic and respectful, never slapstick.",
        "advice": "Prepare the basics and a small example; when lost, ask a clarifying question rather than guessing.",
    },
    "The Cocky One": {
        "profile": (8, 3, 7, 8),
        "blurb": "Overconfident and dismissive, with frequent mistakes beneath the certainty.",
        "style": "Act like you know everything, dismiss checking or advice, and state a plausible but clearly incorrect technical claim as fact. Make frequent factual mistakes, not extravagant achievement claims.",
        "advice": "Check your facts, show your reasoning and welcome corrections instead of dismissing other people.",
    },
    "The Casual One": {
        "profile": (9, 7, 7, 3),
        "blurb": "Informal and relatable, with real substance; slang can also sound unprofessional.",
        "style": "Use light casual lingo such as 'like', 'lowkey' and 'tbh', with a concrete useful action underneath. Do not turn every word into slang.",
        "advice": "Casual language can feel relatable and authentic, but too much slang can sound unprofessional. Match the room and keep the substance.",
    },
}


def select_archetypes():
    return random.sample(list(ARCHETYPES), 3)
