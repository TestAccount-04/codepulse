import React from 'react';
import { RepoStatus } from '../types';
import { Database, FileCode, Layers, ShieldAlert, Sparkles } from 'lucide-react';

interface SidebarProps {
  status: RepoStatus | null;
  files: Array<{ path: string; language: string; symbol_count: number }>;
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  status,
  files,
  selectedFile,
  onSelectFile,
}) => {
  const metrics = status?.metrics;

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/60 backdrop-blur flex flex-col h-[calc(100vh-3.5rem)] select-none">
      {/* Metrics Cards */}
      <div className="p-3 border-b border-slate-800 grid grid-cols-3 gap-2">
        <div className="bg-slate-800/60 border border-slate-700/60 p-2 rounded-lg text-center">
          <div className="text-[10px] text-slate-400 uppercase font-semibold">Files</div>
          <div className="text-base font-bold text-white mt-0.5">{metrics?.file_count ?? 0}</div>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 p-2 rounded-lg text-center">
          <div className="text-[10px] text-slate-400 uppercase font-semibold">Symbols</div>
          <div className="text-base font-bold text-blue-400 mt-0.5">{metrics?.symbol_count ?? 0}</div>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 p-2 rounded-lg text-center">
          <div className="text-[10px] text-slate-400 uppercase font-semibold">Relations</div>
          <div className="text-base font-bold text-indigo-400 mt-0.5">{metrics?.relationship_count ?? 0}</div>
        </div>
      </div>

      {/* Change Status Legend */}
      <div className="p-3 border-b border-slate-800">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <Sparkles className="w-3 h-3 text-blue-400" />
          Status Legend
        </div>
        <div className="grid grid-cols-2 gap-1.5 text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-green-500 shadow-sm shadow-green-500/50" />
            <span className="text-slate-300">Added</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-sm shadow-amber-500/50" />
            <span className="text-slate-300">Modified</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 shadow-sm shadow-red-500/50" />
            <span className="text-slate-300">Deleted</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-sm shadow-blue-500/50" />
            <span className="text-slate-300">Renamed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 shadow-sm shadow-purple-500/50" />
            <span className="text-slate-300">Impacted</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-500" />
            <span className="text-slate-400">Unchanged</span>
          </div>
        </div>
      </div>

      {/* Repository File Tree */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2 py-1 flex items-center justify-between">
          <span>Files ({files.length})</span>
        </div>
        <div className="space-y-0.5 mt-1">
          {files.map((file) => {
            const isSelected = selectedFile === file.path;
            return (
              <button
                key={file.path}
                onClick={() => onSelectFile(file.path)}
                className={`w-full text-left px-2.5 py-1.5 rounded-md text-xs font-mono transition flex items-center justify-between group ${
                  isSelected
                    ? 'bg-blue-600/20 text-blue-300 border border-blue-500/30'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
                title={file.path}
              >
                <div className="flex items-center gap-1.5 min-w-0">
                  <FileCode className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan-400 shrink-0" />
                  <span className="truncate">{file.path}</span>
                </div>
                <span className="text-[10px] text-slate-500 shrink-0 ml-1">
                  {file.symbol_count}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
};
