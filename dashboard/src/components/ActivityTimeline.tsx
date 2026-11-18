import React from 'react';
import { ChangeEvent } from '../types';
import { Activity, Clock, User, X } from 'lucide-react';

interface ActivityTimelineProps {
  events: ChangeEvent[];
  isOpen: boolean;
  onClose: () => void;
}

export const ActivityTimeline: React.FC<ActivityTimelineProps> = ({
  events,
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  return (
    <div className="h-56 border-t border-slate-800 bg-slate-900/95 backdrop-blur flex flex-col z-30 shadow-2xl">
      <div className="h-9 px-4 border-b border-slate-800 flex items-center justify-between text-xs font-semibold text-slate-300">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-400" />
          <span>Live Change Activity Feed ({events.length})</span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {events.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-500 italic">
            Listening for live file modifications and coding agent activity...
          </div>
        ) : (
          events.map((ev) => {
            const badgeColor = {
              added: 'bg-green-500/10 text-green-400 border-green-500/20',
              modified: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
              deleted: 'bg-red-500/10 text-red-400 border-red-500/20',
              renamed: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
            }[ev.event_type] || 'bg-slate-500/10 text-slate-400 border-slate-500/20';

            return (
              <div
                key={ev.id}
                className="flex items-center justify-between gap-4 p-2 rounded-lg bg-slate-800/40 border border-slate-800 hover:border-slate-700 text-xs transition"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${badgeColor}`}>
                    {ev.event_type}
                  </span>
                  <div className="min-w-0">
                    <span className="font-semibold text-white mr-2">{ev.summary}</span>
                    <span className="text-[11px] font-mono text-slate-400">{ev.file_path}</span>
                  </div>
                </div>

                <div className="flex items-center gap-4 shrink-0 text-slate-400 text-[11px]">
                  <div className="flex items-center gap-1">
                    <User className="w-3 h-3 text-slate-500" />
                    <span className="font-mono text-slate-300">{ev.agent_name}</span>
                  </div>
                  <div className="flex items-center gap-1 font-mono text-slate-500">
                    <Clock className="w-3 h-3" />
                    <span>{ev.timestamp ? ev.timestamp.slice(11, 19) : ''}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
