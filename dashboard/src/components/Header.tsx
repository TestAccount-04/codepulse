import React from 'react';
import { Activity, GitBranch, RefreshCw, Search, Wifi, WifiOff } from 'lucide-react';
import { RepoStatus, ChangeStatus } from '../types';

interface HeaderProps {
  status: RepoStatus | null;
  wsConnected: boolean;
  filterStatus: string;
  onFilterChange: (status: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onScan: () => void;
  scanning: boolean;
  timelineOpen: boolean;
  onToggleTimeline: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  wsConnected,
  filterStatus,
  onFilterChange,
  searchQuery,
  onSearchChange,
  onScan,
  scanning,
  timelineOpen,
  onToggleTimeline,
}) => {
  return (
    <header className="h-14 border-b border-slate-800 bg-slate-900/90 backdrop-blur px-4 flex items-center justify-between z-20">
      {/* Brand & Repository */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
            CP
          </div>
          <div>
            <div className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              CodePulse
              <span className="text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-1.5 py-0.2 rounded font-mono">
                v0.1.0
              </span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono truncate max-w-[200px]">
              {status?.repository.split(/[\\/]/).pop() || 'Loading repository...'}
            </div>
          </div>
        </div>

        {status?.branch && (
          <div className="hidden md:flex items-center gap-1.5 text-xs text-slate-300 bg-slate-800 border border-slate-700 px-2.5 py-1 rounded-md">
            <GitBranch className="w-3.5 h-3.5 text-blue-400" />
            <span className="font-mono">{status.branch}</span>
          </div>
        )}
      </div>

      {/* Search & Filters */}
      <div className="flex items-center gap-2.5 max-w-md w-full mx-4">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search classes, methods, functions..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full bg-slate-800/80 border border-slate-700 rounded-md pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <select
          value={filterStatus}
          onChange={(e) => onFilterChange(e.target.value)}
          className="bg-slate-800 border border-slate-700 text-xs text-slate-300 rounded-md px-2.5 py-1 focus:outline-none focus:border-blue-500"
        >
          <option value="all">All Statuses</option>
          <option value="modified">Modified</option>
          <option value="added">Added</option>
          <option value="deleted">Deleted</option>
          <option value="impacted">Impacted</option>
          <option value="unchanged">Unchanged</option>
        </select>
      </div>

      {/* Controls & Connection */}
      <div className="flex items-center gap-2">
        <button
          onClick={onScan}
          disabled={scanning}
          className="flex items-center gap-1.5 text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 px-2.5 py-1.5 rounded-md transition disabled:opacity-50"
          title="Rescan repository"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${scanning ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">{scanning ? 'Scanning...' : 'Scan'}</span>
        </button>

        <button
          onClick={onToggleTimeline}
          className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md border transition ${
            timelineOpen
              ? 'bg-blue-600/20 border-blue-500 text-blue-300'
              : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
          }`}
          title="Toggle live change feed"
        >
          <Activity className="w-3.5 h-3.5 text-blue-400" />
          <span className="hidden sm:inline">Activity</span>
        </button>

        <div
          className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-md border ${
            wsConnected
              ? 'bg-emerald-950/40 border-emerald-800 text-emerald-400'
              : 'bg-rose-950/40 border-rose-800 text-rose-400'
          }`}
          title={wsConnected ? 'WebSocket live streaming active' : 'WebSocket disconnected'}
        >
          {wsConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          <span className="hidden md:inline font-medium">{wsConnected ? 'Live' : 'Offline'}</span>
        </div>
      </div>
    </header>
  );
};
