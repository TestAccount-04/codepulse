export type ChangeStatus = 'added' | 'modified' | 'deleted' | 'renamed' | 'impacted' | 'unchanged';

export type SymbolType = 'file' | 'class' | 'function' | 'method' | 'interface' | 'module';

export interface SymbolNodeData {
  label: string;
  name: string;
  type: SymbolType;
  status: ChangeStatus;
  signature?: string;
  file_path: string;
  start_line?: number;
  end_line?: number;
  docstring?: string;
  [key: string]: unknown;
}

export interface FileNodeData {
  label: string;
  name: string;
  type: 'file';
  file_path: string;
  symbol_count: number;
  [key: string]: unknown;
}

export interface RepoMetrics {
  file_count: number;
  symbol_count: number;
  relationship_count: number;
  languages: Record<string, number>;
  last_scanned_at?: string;
}

export interface RepoStatus {
  repository: string;
  database: string;
  is_git_repo: boolean;
  head_commit?: string;
  branch?: string;
  metrics: RepoMetrics;
  uncommitted_files: {
    modified: string[];
    untracked: string[];
    staged: string[];
    deleted: string[];
    renamed: string[];
  };
}

export interface ChangeEvent {
  id: string;
  timestamp: string;
  event_type: string;
  file_path: string;
  symbol_id?: string;
  session_id?: string;
  agent_name: string;
  diff_content?: string;
  summary?: string;
}

export interface BlastRadius {
  target_symbol_id: string;
  target_name: string;
  max_depth: number;
  upstream_callers_count: number;
  upstream_callers: string[];
  downstream_dependencies_count: number;
  downstream_dependencies: string[];
}

export type ReviewStatus = 'pending' | 'reviewed' | 'accepted' | 'rejected';

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

