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
