import {
  AgentSessionSummary,
  CodePulseSymbol,
  RepoStatus,
  ReviewAnnotation,
  ReviewDetail,
  ReviewItem,
  ReviewStatus,
} from './types';

export class CodePulseClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://127.0.0.1:8000') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  setBaseUrl(url: string): void {
    this.baseUrl = url.replace(/\/$/, '');
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  async isHealthy(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/api/status`, { method: 'GET' });
      return res.ok;
    } catch {
      return false;
    }
  }

  async getStatus(): Promise<RepoStatus> {
    const res = await fetch(`${this.baseUrl}/api/status`);
    if (!res.ok) {
      throw new Error(`Failed to fetch status: HTTP ${res.status}`);
    }
    return (await res.json()) as RepoStatus;
  }

  async getChangedSymbols(): Promise<CodePulseSymbol[]> {
    const res = await fetch(`${this.baseUrl}/api/changes`);
    if (!res.ok) {
      throw new Error(`Failed to fetch changed symbols: HTTP ${res.status}`);
    }
    return (await res.json()) as CodePulseSymbol[];
  }

  async getReviews(status?: ReviewStatus): Promise<ReviewItem[]> {
    const url = status
      ? `${this.baseUrl}/api/reviews?status=${encodeURIComponent(status)}`
      : `${this.baseUrl}/api/reviews`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Failed to fetch reviews: HTTP ${res.status}`);
    }
    return (await res.json()) as ReviewItem[];
  }

  async getReviewDetail(symbolId: string): Promise<ReviewDetail> {
    const res = await fetch(`${this.baseUrl}/api/reviews/${encodeURIComponent(symbolId)}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch review detail: HTTP ${res.status}`);
    }
    return (await res.json()) as ReviewDetail;
  }

  async setReviewStatus(
    symbolId: string,
    status: ReviewStatus,
    note?: string,
    decisionReason?: string
  ): Promise<ReviewItem> {
    const res = await fetch(`${this.baseUrl}/api/reviews/${encodeURIComponent(symbolId)}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status,
        note,
        decision_reason: decisionReason,
        author: 'vscode-reviewer',
      }),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to update review status: ${err}`);
    }
    return (await res.json()) as ReviewItem;
  }

  async addReviewNote(symbolId: string, note: string): Promise<ReviewAnnotation> {
    const res = await fetch(`${this.baseUrl}/api/reviews/${encodeURIComponent(symbolId)}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        note,
        author: 'vscode-reviewer',
      }),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to add review note: ${err}`);
    }
    return (await res.json()) as ReviewAnnotation;
  }

  async rollbackSymbol(symbolId: string, reason?: string): Promise<{ success: boolean; message?: string }> {
    const res = await fetch(`${this.baseUrl}/api/reviews/${encodeURIComponent(symbolId)}/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reason: reason || 'Rollback requested from VS Code extension',
        safe_rollback: true,
        author: 'vscode-reviewer',
      }),
    });
    const data = (await res.json()) as { success: boolean; message?: string; detail?: string };
    if (!res.ok) {
      throw new Error(data.detail || 'Rollback failed');
    }
    return data;
  }

  async getActiveSessions(): Promise<AgentSessionSummary[]> {
    const res = await fetch(`${this.baseUrl}/api/sessions?limit=5`);
    if (!res.ok) {
      throw new Error(`Failed to fetch sessions: HTTP ${res.status}`);
    }
    return (await res.json()) as AgentSessionSummary[];
  }
}
