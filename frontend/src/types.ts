export type AudienceType = 'citizen' | 'business';
export type VerdictStatus = 'YES' | 'NO' | 'MAYBE';

export interface Condition {
  field: string;
  operator: string;
  value: any;
  unit?: string;
  clause_id: string;
  quote: string;
}

export interface Benefit {
  description: string;
  amount?: number | null;
  frequency?: string;
  clause_id: string;
  quote: string;
}

export interface Obligation {
  description: string;
  deadline?: string;
  required_documents: string[];
  apply_at?: string;
  clause_id: string;
  quote: string;
}

export interface Scheme {
  doc_id: string;
  title: string;
  audience: AudienceType;
  conditions: Condition[];
  benefits: Benefit[];
  obligations: Obligation[];
  uncertain: any[];
  confidence: number;
}

export interface InterviewQuestion {
  field: string;
  question_text: string;
  input_type: string;
  options?: string[];
  choices?: string[];
  unit?: string;
  default_value?: any;
  help_text?: string;
}

export interface Reason {
  condition: Condition;
  passed: boolean;
  explanation: string;
  clause_id: string;
}

export interface Verdict {
  status: VerdictStatus;
  reasons: Reason[];
  missing_fields: string[];
  summary: string;
}

export interface Segment {
  text: string;
  clause_ids: string[];
  audio_url?: string;
}

export interface Explainer {
  language: string;
  verdict_segment?: Segment;
  segments: Segment[];
  checklist: string[];
  audio_urls: string[];
}

export interface TraceStep {
  node: string;
  status: string;
  latency_ms?: number;
  timestamp?: string;
}

export interface ExtractionProgress {
  current_section: number;
  total_sections: number;
  percent: number;
  estimated_seconds_remaining: number;
  stage: string;
}

export interface PipelineStatus {
  run_id: string;
  status: 'started' | 'running' | 'waiting_for_answers' | 'completed' | 'error';
  current_node?: string;
  error?: string;
  progress?: ExtractionProgress;
  scheme?: Scheme;
  questions?: InterviewQuestion[];
  verdict?: Verdict;
  explainer?: Explainer;
  trace?: TraceStep[];
}

export interface VerifiedSource {
  title: string;
  url: string;
  category: string;
}

export interface PipelineStartResponse {
  run_id: string;
  doc_id?: string;
}

