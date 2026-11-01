export type Job = {
  title: string;
  company: string;
  seniority: string;
  education: string;
  skills: string[];
  responsibilities: string[];
  summary: string;
};
export type Candidate = {
  id: string;
  name: string;
  voice_id: string;
  intro_line: string;
  archetype: string;
  archetype_blurb: string;
  attributes: Record<string, number>;
  resume: {
    education: string;
    experience: string[];
    skills: string[];
    projects: string[];
  };
  fabricated_claims: string[];
};
export type Turn = { q: string; a: string; kind: string };
export type Questions = {
  behavioural: string;
  technical: string;
  behavioural_tests: string;
  technical_tests: string;
  special: { kind: "followup" | "resume"; text: string; tests: string };
};
export type Rating = {
  communication: number;
  evidence: number;
  honesty: number;
  job_fit: number;
};
export type Lesson = { candidate_id: string; quote: string; advice: string };
export type Evaluation = {
  dos: Lesson[];
  donts: Lesson[];
  annotations: Record<
    string,
    {
      tone: "good" | "bad" | "neutral";
      label: string;
      why_interviewers_notice: string;
    }[]
  >;
  rating_comparisons: {
    id: string;
    truth: Rating;
    user: Rating | null;
    flags: string[];
  }[];
  best_fit_id: string;
  hired_was_best: boolean;
  interviewer_score: number;
  verdict: string;
  candidate_summaries: {
    id: string;
    summary: string;
    bluffs_caught: string[];
    bluffs_missed: string[];
  }[];
  best_questions: { text: string; why: string }[];
  weak_questions: { text: string; why: string }[];
  tips: string[];
};
