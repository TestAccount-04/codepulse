import React, { useEffect, useState } from 'react';
import { SymbolNodeData, BlastRadius } from '../types';
import { ArrowDownRight, ArrowUpRight, Code, FileText, GitCompare, ShieldAlert, X } from 'lucide-react';

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
  const [activeTab, setActiveTab] = useState<'info' | 'diff' | 'impact'>('info');
  const [diffText, setDiffText] = useState<string>('');
  const [blastRadius, setBlastRadius] = useState<BlastRadius | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedNode) return;

    // Fetch diff
    fetch(`/api/diff/${encodeURIComponent(selectedNode.file_path)}`)
      .then((r) => r.json())
      .then((data) => setDiffText(data.diff || ''))
      .catch(() => setDiffText(''));

    // Fetch blast radius
    const symbolId = `${selectedNode.file_path}::${selectedNode.type}::${selectedNode.name}`;
    fetch(`/api/symbols/${encodeURIComponent(symbolId)}/blast-radius`)
      .then((r) => r.json())
      .then((data) => setBlastRadius(data))
      .catch(() => setBlastRadius(null));
  }, [selectedNode]);

  if (!selectedNode) return null;

  return (
    <div className="w-96 border-l border-slate-800 bg-slate-900/95 backdrop-blur flex flex-col h-[calc(100vh-3.5rem)] shadow-2xl z-20">
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

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
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
            {/* Upstream Callers */}
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

            {/* Downstream Dependencies */}
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
