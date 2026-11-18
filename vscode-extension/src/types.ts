export type ReviewStatus = 'pending' | 'reviewed' | 'accepted' | 'rejected';

export type ChangeStatus = 'added' | 'modified' | 'deleted' | 'renamed' | 'unchanged' | 'impacted';

export interface CodePulseSymbol {
  id: string;
  repo_id: string;
  file_path: string;
  name: string;
  symbol_type: string;
  start_line: number;
  end_line: number;
  signature?: string;
  docstring?: string;
  change_status: ChangeStatus;
}

export interface ReviewAnnotation {
  id: string;
  repo_id: string;
  symbol_id: string;
  author: string;
  note: string;
  created_at: string;
}

export interface ReviewItem {
  id: string;
  repo_id: string;
  symbol_id: string;
  file_path: string;
  status: ReviewStatus;
  decision_reason?: string;
  updated_at: string;
  annotations: ReviewAnnotation[];
}

export interface ReviewDetail {
  symbol_id: string;
  symbol_name: string;
  file_path: string;
  status: ReviewStatus;
  change_status: ChangeStatus;
  decision_reason?: string;
  original_code?: string;
  updated_code?: string;
  diff_text?: string;
  structural_summary?: string;
  task_context?: string;
  impact_report?: {
    risk_level: string;
    risk_score: number;
    direct_callers: Array<{ caller_name: string; file_path: string; line: number }>;
    indirect_callers: string[];
    related_tests: string[];
  };
  explanation?: {
    what_changed: string;
    why: string;
    impact: string;
    risk_level: string;
  };
  agent_session?: {
    id: string;
    agent_name: string;
    task_description?: string;
  };
  annotations: ReviewAnnotation[];
}

export interface RepoStatus {
  repository: string;
  database: string;
  is_git_repo: boolean;
  head_commit?: string;
  branch?: string;
  metrics: {
    file_count: number;
    symbol_count: number;
    relationship_count: number;
    languages: Record<string, number>;
    last_scanned_at?: string;
  };
  uncommitted_files: {
    modified: string[];
    untracked: string[];
    staged: string[];
    deleted: string[];
    renamed: string[];
  };
}

export interface AgentSessionSummary {
  id: string;
  repo_id: string;
  agent_name: string;
  task_description?: string;
  started_at: string;
  ended_at?: string;
  status: string;
}
