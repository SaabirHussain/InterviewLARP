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


class Questions(BaseModel):
    behavioural: str
    technical: str
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


class Evaluation(BaseModel):
    best_fit_id: str
    hired_was_best: bool
    interviewer_score: int = Field(ge=1, le=100)
    verdict: str
    candidate_summaries: list[CandidateSummary]
    best_questions: list[QuestionReview]
    weak_questions: list[QuestionReview]
    tips: list[str]


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
