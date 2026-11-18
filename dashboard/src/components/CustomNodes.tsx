import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { SymbolNodeData, FileNodeData, ChangeStatus } from '../types';
import { Box, Code, FileCode, Layers, ShieldAlert } from 'lucide-react';

const statusConfig: Record<ChangeStatus, { border: string; bg: string; text: string; label: string }> = {
  added: { border: 'border-green-500', bg: 'bg-green-950/40', text: 'text-green-400', label: 'Added' },
  modified: { border: 'border-amber-500', bg: 'bg-amber-950/40', text: 'text-amber-400', label: 'Modified' },
  deleted: { border: 'border-red-500', bg: 'bg-red-950/40', text: 'text-red-400', label: 'Deleted' },
  renamed: { border: 'border-blue-500', bg: 'bg-blue-950/40', text: 'text-blue-400', label: 'Renamed' },
  impacted: { border: 'border-purple-500', bg: 'bg-purple-950/40', text: 'text-purple-400', label: 'Impacted' },
  unchanged: { border: 'border-slate-700', bg: 'bg-slate-900/80', text: 'text-slate-400', label: 'Unchanged' },
};

export const SymbolNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as unknown as SymbolNodeData;
  const config = statusConfig[nodeData.status] || statusConfig.unchanged;

  const getTypeIcon = () => {
    switch (nodeData.type) {
      case 'class':
        return <Box className="w-3.5 h-3.5 text-amber-400" />;
      case 'method':
      case 'function':
        return <Code className="w-3.5 h-3.5 text-blue-400" />;
      case 'interface':
        return <Layers className="w-3.5 h-3.5 text-purple-400" />;
      default:
        return <FileCode className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div
      className={`relative px-3 py-2 rounded-lg border shadow-md transition-all duration-150 min-w-[240px] max-w-[320px] ${config.border} ${config.bg} ${
        selected ? 'ring-2 ring-blue-400 ring-offset-2 ring-offset-slate-900 shadow-blue-500/20' : ''
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-500 !w-2 !h-2" />

      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="flex items-center gap-1.5 min-w-0">
          {getTypeIcon()}
          <span className="text-xs uppercase font-semibold tracking-wider text-slate-400">
            {nodeData.type}
          </span>
        </div>
        <span
          className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full border ${config.border} ${config.text}`}
        >
          {config.label}
        </span>
      </div>

      <div className="text-sm font-semibold text-white truncate" title={nodeData.name}>
        {nodeData.name}
      </div>

      {nodeData.signature && (
        <div
          className="text-[11px] font-mono text-slate-400 truncate mt-0.5 bg-black/30 px-1.5 py-0.5 rounded"
          title={nodeData.signature}
        >
          {nodeData.signature}
        </div>
      )}

      {nodeData.status === 'impacted' && (
        <div className="mt-1 flex items-center gap-1 text-[10px] text-purple-300">
          <ShieldAlert className="w-3 h-3 text-purple-400" />
          <span>Downstream dependent impacted</span>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-slate-500 !w-2 !h-2" />
    </div>
  );
});

export const FileNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as unknown as FileNodeData;

  return (
    <div
      className={`px-4 py-2.5 rounded-lg border border-slate-700 bg-slate-800/90 shadow-lg min-w-[300px] ${
        selected ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-slate-900' : ''
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <FileCode className="w-4 h-4 text-cyan-400 shrink-0" />
          <span className="font-mono text-xs font-semibold text-slate-200 truncate" title={nodeData.file_path}>
            {nodeData.file_path}
          </span>
        </div>
        <span className="text-[11px] bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full shrink-0">
          {nodeData.symbol_count} symbols
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-cyan-500 !w-2 !h-2" />
    </div>
  );
});
