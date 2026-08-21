import React from 'react';
import { Skull, Key, Clock, ShieldX } from 'lucide-react';

export default function KilledSessions({ logs, isGlowing }) {
  // Extract killed log items
  const killedLogs = logs.filter((log) => log.status === 'killed');

  return (
    <div 
      className={`soc-card rounded-2xl p-6 flex flex-col h-full transition-all duration-500 ${
        isGlowing 
          ? 'ring-4 ring-rose-500/90 border-rose-500 soc-glow-rose-strong animate-pulse-glow scale-[1.015]' 
          : 'soc-glow-rose/20'
      }`}
    >
      
      {/* Panel Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <div className={`p-1.5 rounded border transition-colors ${
            isGlowing 
              ? 'bg-rose-500 text-white border-rose-300 animate-bounce' 
              : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
          }`}>
            <Skull className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono">
              KILLED SESSIONS
            </h3>
            <p className="text-[11px] text-slate-400">
              Revoked session tokens blocked by inline GateGuard proxy
            </p>
          </div>
        </div>

        <div className={`px-2.5 py-1 rounded-md text-xs font-bold font-mono transition-all ${
          isGlowing
            ? 'bg-rose-600 text-white border border-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.9)] animate-pulse'
            : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
        }`}>
          {killedLogs.length} BLOCKED
        </div>
      </div>

      {/* Sessions List */}
      <div className="mt-4 overflow-y-auto max-h-[380px] space-y-3 pr-1">
        {killedLogs.length === 0 ? (
          <div className="p-8 text-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-xl">
            No session tokens killed yet.
          </div>
        ) : (
          killedLogs.map((item, index) => (
            <div
              key={index}
              className={`bg-slate-900/80 border rounded-xl p-3 font-mono text-xs transition-all hover:translate-x-1 ${
                index === 0 && isGlowing
                  ? 'border-rose-400 bg-rose-950/40 shadow-[0_0_20px_rgba(244,63,94,0.5)] scale-[1.02]'
                  : 'border-rose-500/30 hover:border-rose-500/60'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                {/* Truncated Session Token */}
                <div className="flex items-center space-x-1.5 text-rose-400 font-bold">
                  <Key className="w-3.5 h-3.5" />
                  <span>{item.token_hash}</span>
                  {index === 0 && isGlowing && (
                    <span className="px-1.5 py-0.2 bg-rose-500 text-white text-[9px] uppercase font-extrabold rounded animate-ping">
                      NEW
                    </span>
                  )}
                </div>

                {/* Kill Timestamp */}
                <div className="flex items-center space-x-1 text-slate-400 text-[11px]">
                  <Clock className="w-3 h-3 text-slate-500" />
                  <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>

              {/* Attack Vector & Source IP */}
              <div className="text-[11px] text-slate-300 bg-slate-950/70 p-2 rounded border border-slate-800 space-y-1">
                <div className="flex items-center justify-between text-slate-400 text-[10px]">
                  <span>TRIGGER PATH</span>
                  <span className="text-rose-400 font-bold">RISK SCORE: {item.risk_score}</span>
                </div>
                <div className="text-rose-300 font-semibold truncate" title={item.path}>
                  {item.path}
                </div>
                <div className="text-slate-400 text-[10px] pt-0.5 flex justify-between">
                  <span>SOURCE IP: {item.ip}</span>
                  <span className="text-slate-500">ACTION: TERMINATED</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

    </div>
  );
}

