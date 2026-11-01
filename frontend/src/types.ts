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
  special: { kind: "followup" | "resume"; text: string };
};
export type Evaluation = {
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
