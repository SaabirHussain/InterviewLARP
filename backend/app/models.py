from typing import Literal

from pydantic import BaseModel, Field


class Job(BaseModel):
    title: str = Field(min_length=1)
    company: str = ""
    seniority: str
    education: str
    skills: list[str]
    responsibilities: list[str]
    summary: str


class Attributes(BaseModel):
    mood: int = Field(ge=1, le=10)
    smartness: int = Field(ge=1, le=10)
    charisma: int = Field(ge=1, le=10)
    larping: int = Field(ge=1, le=10)


class Resume(BaseModel):
    education: str
    experience: list[str] = Field(min_length=1)
    skills: list[str]
    projects: list[str]


class Candidate(BaseModel):
    id: str
    name: str
    voice_id: str
    intro_line: str
    archetype: str = Field(min_length=1)
    archetype_blurb: str = Field(min_length=1)
    attributes: Attributes
    resume: Resume
    fabricated_claims: list[str] = Field(min_length=1, max_length=3)


class CandidateBatch(BaseModel):
    candidates: list[Candidate] = Field(min_length=3, max_length=3)


class Turn(BaseModel):
    q: str
    a: str
    kind: str


class Special(BaseModel):
    kind: Literal["followup", "resume"]
    text: str
    tests: str = Field(min_length=1)


class Questions(BaseModel):
    behavioural: str
    technical: str
    behavioural_tests: str = Field(min_length=1)
    technical_tests: str = Field(min_length=1)
    special: Special


class Answer(BaseModel):
    answer: str = Field(min_length=1)


class CandidateSummary(BaseModel):
    id: str
    summary: str
    bluffs_caught: list[str]
    bluffs_missed: list[str]


class QuestionReview(BaseModel):
    text: str
    why: str


class Rating(BaseModel):
    communication: int = Field(ge=1, le=5)
    evidence: int = Field(ge=1, le=5)
    honesty: int = Field(ge=1, le=5)
    job_fit: int = Field(ge=1, le=5)


class RatingComparison(BaseModel):
    id: str
    truth: Rating
    user: Rating | None
    flags: list[str]


class Annotation(BaseModel):
    tone: Literal['good', 'bad', 'neutral']
    label: str = Field(min_length=1)
    why_interviewers_notice: str = Field(min_length=1)


class Lesson(BaseModel):
    candidate_id: str
    quote: str = Field(min_length=1)
    advice: str = Field(min_length=1)


class Evaluation(BaseModel):
    best_fit_id: str
    hired_was_best: bool
    interviewer_score: int = Field(ge=1, le=100)
    verdict: str
    candidate_summaries: list[CandidateSummary]
    best_questions: list[QuestionReview]
    weak_questions: list[QuestionReview]
    tips: list[str]
    annotations: dict[str, list[Annotation]]
    dos: list[Lesson] = Field(max_length=3)
    donts: list[Lesson] = Field(max_length=3)
    rating_comparisons: list[RatingComparison]


class JobRequest(BaseModel):
    job: Job


class QuestionRequest(JobRequest):
    candidate: Candidate
    transcript: list[Turn] = Field(default_factory=list)
    round: int = Field(ge=1, le=3)


class AnswerRequest(JobRequest):
    candidate: Candidate
    transcript: list[Turn] = Field(default_factory=list)
    question: str = Field(min_length=1, max_length=4000)


class EvaluateRequest(JobRequest):
    candidates: list[Candidate] = Field(min_length=3, max_length=3)
    transcripts: dict[str, list[Turn]]
    hired_id: str
    ratings: dict[str, Rating] = Field(default_factory=dict)
