import React, { useEffect, useState } from 'react';
import { SymbolNodeData, BlastRadius, ReviewDetail, ReviewStatus } from '../types';
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  CheckCircle2,
  FileText,
  GitCompare,
  MessageSquare,
  RotateCcw,
  ShieldAlert,
  X,
  XCircle,
} from 'lucide-react';

interface DetailsPanelProps {
  selectedNode: SymbolNodeData | null;
  onClose: () => void;
  onFocusSymbol?: (symbolId: string) => void;
}

export const DetailsPanel: React.FC<DetailsPanelProps> = ({
  selectedNode,
  onClose,
  onFocusSymbol,
}) => {
  const [activeTab, setActiveTab] = useState<'info' | 'diff' | 'impact' | 'review'>('info');
  const [diffText, setDiffText] = useState<string>('');
  const [blastRadius, setBlastRadius] = useState<BlastRadius | null>(null);
  const [reviewDetail, setReviewDetail] = useState<ReviewDetail | null>(null);
  const [newNote, setNewNote] = useState<string>('');
  const [reviewLoading, setReviewLoading] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const symbolId = selectedNode
    ? `${selectedNode.file_path}::${selectedNode.type}::${selectedNode.name}`
    : '';

  const fetchReviewDetail = () => {
    if (!symbolId) return;
    setReviewLoading(true);
    fetch(`/api/reviews/${encodeURIComponent(symbolId)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        setReviewDetail(data);
        setReviewLoading(false);
      })
      .catch(() => setReviewLoading(false));
  };

  useEffect(() => {
    if (!selectedNode) return;

    // Fetch diff
    fetch(`/api/diff/${encodeURIComponent(selectedNode.file_path)}`)
      .then((r) => r.json())
      .then((data) => setDiffText(data.diff || ''))
      .catch(() => setDiffText(''));

    // Fetch blast radius
    fetch(`/api/symbols/${encodeURIComponent(symbolId)}/blast-radius`)
      .then((r) => r.json())
      .then((data) => setBlastRadius(data))
      .catch(() => setBlastRadius(null));

    fetchReviewDetail();
    setActionMessage(null);
  }, [selectedNode, symbolId]);

  const handleSetStatus = async (status: ReviewStatus) => {
    if (!symbolId) return;
    setReviewLoading(true);
    try {
      const res = await fetch(`/api/reviews/${encodeURIComponent(symbolId)}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, author: 'reviewer' }),
      });
      if (res.ok) {
        setActionMessage(`Status updated to ${status.toUpperCase()}`);
        fetchReviewDetail();
      }
    } catch (e) {
      setActionMessage('Failed to update status');
    } finally {
      setReviewLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!symbolId) return;
    if (!window.confirm(`Are you sure you want to reject and rollback '${selectedNode?.name}'? Unrelated edits will be preserved.`)) {
      return;
    }
    setReviewLoading(true);
    try {
      const res = await fetch(`/api/reviews/${encodeURIComponent(symbolId)}/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Rejected by reviewer in dashboard', safe_rollback: true }),
      });
      const data = await res.json();
      if (res.ok) {
        setActionMessage(data.message || 'Symbol rolled back successfully');
        fetchReviewDetail();
      } else {
        setActionMessage(`Rollback failed: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      setActionMessage('Rollback request failed');
    } finally {
      setReviewLoading(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim() || !symbolId) return;
    try {
      const res = await fetch(`/api/reviews/${encodeURIComponent(symbolId)}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: newNote.trim(), author: 'reviewer' }),
      });
      if (res.ok) {
        setNewNote('');
        fetchReviewDetail();
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (!selectedNode) return null;

  return (
    <div className="w-[28rem] border-l border-slate-800 bg-slate-900/95 backdrop-blur flex flex-col h-[calc(100vh-3.5rem)] shadow-2xl z-20">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-start justify-between">
        <div className="min-w-0 pr-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              {selectedNode.type}
            </span>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              {selectedNode.status}
            </span>
            {reviewDetail?.status && (
              <span
                className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${
                  reviewDetail.status === 'accepted'
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : reviewDetail.status === 'rejected'
                    ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                    : reviewDetail.status === 'reviewed'
                    ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
                    : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                }`}
              >
                {reviewDetail.status}
              </span>
            )}
          </div>
          <h2 className="text-base font-bold text-white truncate" title={selectedNode.name}>
            {selectedNode.name}
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5 truncate" title={selectedNode.file_path}>
            {selectedNode.file_path}:{selectedNode.start_line}-{selectedNode.end_line}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 text-xs bg-slate-950/40 px-2">
        <button
          onClick={() => setActiveTab('info')}
          className={`px-3 py-2 border-b-2 font-medium transition flex items-center gap-1.5 ${
            activeTab === 'info'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Overview
        </button>
        <button
          onClick={() => setActiveTab('review')}
          className={`px-3 py-2 border-b-2 font-medium transition flex items-center gap-1.5 ${
            activeTab === 'review'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          Review Panel
        </button>
        <button
          onClick={() => setActiveTab('diff')}
          className={`px-3 py-2 border-b-2 font-medium transition flex items-center gap-1.5 ${
            activeTab === 'diff'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <GitCompare className="w-3.5 h-3.5" />
          Git Diff
        </button>
        <button
          onClick={() => setActiveTab('impact')}
          className={`px-3 py-2 border-b-2 font-medium transition flex items-center gap-1.5 ${
            activeTab === 'impact'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          Blast Radius
        </button>
      </div>

      {/* Action Notification */}
      {actionMessage && (
        <div className="px-4 py-2 bg-slate-800/80 border-b border-slate-700 text-xs text-sky-300 flex items-center justify-between">
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activeTab === 'review' && (
          <div className="space-y-4 text-xs">
            {/* Review Action Controls */}
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Review Decision
              </label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  disabled={reviewLoading}
                  onClick={() => handleSetStatus('accepted')}
                  className="px-2.5 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 flex items-center justify-center gap-1.5 font-medium transition disabled:opacity-50"
                  title="Accept this change (preserves repo files)"
                >
                  <Check className="w-3.5 h-3.5" />
                  Accept
                </button>
                <button
                  disabled={reviewLoading}
                  onClick={() => handleSetStatus('reviewed')}
                  className="px-2.5 py-1.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20 hover:bg-sky-500/20 flex items-center justify-center gap-1.5 font-medium transition disabled:opacity-50"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Reviewed
                </button>
                <button
                  disabled={reviewLoading}
                  onClick={handleRollback}
                  className="px-2.5 py-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 flex items-center justify-center gap-1.5 font-medium transition disabled:opacity-50"
                  title="Reject change and execute safe Git rollback"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Reject
                </button>
              </div>
            </div>

            {/* Change Explanation */}
            {reviewDetail?.explanation && (
              <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-300">Grounded Explanation</span>
                  <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
                    Risk: {reviewDetail.explanation.risk_level}
                  </span>
                </div>
                <div className="space-y-1.5 text-slate-300">
                  <div>
                    <span className="text-emerald-400 font-medium">What: </span>
                    {reviewDetail.explanation.what_changed}
                  </div>
                  <div>
                    <span className="text-amber-400 font-medium">Why: </span>
                    {reviewDetail.explanation.why}
                  </div>
                  <div>
                    <span className="text-purple-400 font-medium">Impact: </span>
                    {reviewDetail.explanation.impact}
                  </div>
                </div>
              </div>
            )}

            {/* Code Comparison */}
            {(reviewDetail?.original_code || reviewDetail?.updated_code) && (
              <div className="space-y-2">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Original vs Updated Code
                </label>
                <div className="space-y-2">
                  <div>
                    <div className="text-[10px] text-slate-400 font-medium mb-1">Original (Git HEAD)</div>
                    <pre className="p-2 bg-black/60 border border-slate-800 rounded-lg text-slate-400 font-mono text-[11px] overflow-x-auto max-h-36">
                      {reviewDetail.original_code || '(Newly Added / No HEAD revision)'}
                    </pre>
                  </div>
                  <div>
                    <div className="text-[10px] text-emerald-400 font-medium mb-1">Updated (Current)</div>
                    <pre className="p-2 bg-emerald-950/20 border border-emerald-900/40 rounded-lg text-emerald-200 font-mono text-[11px] overflow-x-auto max-h-36">
                      {reviewDetail.updated_code || '(Deleted / Empty)'}
                    </pre>
                  </div>
                </div>
              </div>
            )}

            {/* Review Annotations */}
            <div className="space-y-2">
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
                Review Annotations ({reviewDetail?.annotations?.length || 0})
              </label>
              
              {/* Add Note Form */}
              <form onSubmit={handleAddNote} className="flex gap-2">
                <input
                  type="text"
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  placeholder="Add a review note..."
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
                <button
                  type="submit"
                  disabled={!newNote.trim()}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition disabled:opacity-40"
                >
                  Post
                </button>
              </form>

              {/* Note List */}
              <div className="space-y-1.5 pt-1">
                {reviewDetail?.annotations && reviewDetail.annotations.length > 0 ? (
                  reviewDetail.annotations.map((ann) => (
                    <div key={ann.id} className="p-2 rounded-lg bg-slate-950/40 border border-slate-800 space-y-0.5">
                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span className="font-semibold text-blue-400">{ann.author}</span>
                        <span>{ann.created_at.slice(11, 19)}</span>
                      </div>
                      <p className="text-slate-300 text-xs">{ann.note}</p>
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500 italic text-xs">No review notes recorded yet.</div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'info' && (
          <div className="space-y-4 text-xs">
            {selectedNode.signature && (
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                  Signature
                </label>
                <div className="font-mono bg-black/40 border border-slate-800 p-2.5 rounded-lg text-slate-200 overflow-x-auto">
                  {selectedNode.signature}
                </div>
              </div>
            )}

            {selectedNode.docstring ? (
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                  Documentation
                </label>
                <div className="bg-slate-800/40 border border-slate-800 p-2.5 rounded-lg text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {selectedNode.docstring}
                </div>
              </div>
            ) : (
              <div className="text-slate-500 italic">No docstring available for this symbol.</div>
            )}
          </div>
        )}

        {activeTab === 'diff' && (
          <div>
            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
              File Diff vs HEAD
            </label>
            {diffText ? (
              <div className="font-mono text-[11px] bg-black/60 border border-slate-800 p-2 rounded-lg overflow-x-auto space-y-0.5">
                {diffText.split('\n').map((line, idx) => {
                  let colorClass = 'text-slate-300';
                  if (line.startsWith('+') && !line.startsWith('+++')) colorClass = 'text-green-400 bg-green-950/30';
                  if (line.startsWith('-') && !line.startsWith('---')) colorClass = 'text-red-400 bg-red-950/30';
                  if (line.startsWith('@@')) colorClass = 'text-cyan-400';
                  return (
                    <div key={idx} className={`${colorClass} px-1 rounded`}>
                      {line}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-slate-500 text-xs italic">
                No uncommitted Git modifications detected for this file.
              </div>
            )}
          </div>
        )}

        {activeTab === 'impact' && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <ArrowUpRight className="w-3.5 h-3.5 text-purple-400" />
                  Upstream Callers ({blastRadius?.upstream_callers_count ?? 0})
                </label>
              </div>
              {blastRadius?.upstream_callers && blastRadius.upstream_callers.length > 0 ? (
                <div className="space-y-1">
                  {blastRadius.upstream_callers.map((caller) => (
                    <div
                      key={caller}
                      onClick={() => onFocusSymbol?.(caller)}
                      className="p-2 rounded bg-purple-950/20 border border-purple-900/40 text-xs font-mono text-purple-300 hover:border-purple-500 cursor-pointer transition truncate"
                      title={caller}
                    >
                      {caller}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-slate-500 text-xs italic">No upstream callers directly detected.</div>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <ArrowDownRight className="w-3.5 h-3.5 text-blue-400" />
                  Downstream Invocations ({blastRadius?.downstream_dependencies_count ?? 0})
                </label>
              </div>
              {blastRadius?.downstream_dependencies && blastRadius.downstream_dependencies.length > 0 ? (
                <div className="space-y-1">
                  {blastRadius.downstream_dependencies.map((dep) => (
                    <div
                      key={dep}
                      className="p-2 rounded bg-blue-950/20 border border-blue-900/40 text-xs font-mono text-blue-300 truncate"
                      title={dep}
                    >
                      {dep}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-slate-500 text-xs italic">No downstream calls extracted.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
