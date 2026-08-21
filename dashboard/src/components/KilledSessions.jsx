import React from 'react';
import { Skull, Key, Clock, ShieldX, Ban } from 'lucide-react';

export default function KilledSessions({ logs, isGlowing }) {
  // Extract killed & blocklisted log items
  const killedLogs = logs.filter((log) => log.status === 'killed' || log.status === 'blocklisted');

  return (
    <div 
      className={`soc-card rounded-2xl p-6 flex flex-col h-full transition-all duration-300 ${
        isGlowing 
          ? 'animate-pulse-glow-3x' 
          : 'border-slate-800'
      }`}
    >
      
      {/* Panel Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <div className={`p-1.5 rounded border transition-colors ${
            isGlowing 
              ? 'bg-rose-500/30 text-rose-300 border-rose-400 animate-pop-3x' 
              : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
          }`}>
            <Skull className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono">
              KILLED & BLOCKED SESSIONS
            </h3>
            <p className="text-[11px] text-slate-400">
              Revoked session tokens blocked by inline GateGuard proxy
            </p>
          </div>
        </div>

        <div className={`px-2.5 py-1 rounded-md text-xs font-bold font-mono transition-all ${
          isGlowing
            ? 'bg-rose-600 text-white border border-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.8)] animate-pop-3x'
            : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
        }`}>
          {killedLogs.length} BLOCKED
        </div>
      </div>

      {/* Sessions List */}
      <div className="mt-4 overflow-y-auto max-h-[380px] space-y-3 pr-1">
        {killedLogs.length === 0 ? (
          <div className="p-8 text-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-xl">
            No session tokens killed or blocklisted yet.
          </div>
        ) : (
          killedLogs.map((item, index) => {
            const isBlocklisted = item.status === 'blocklisted';
            return (
              <div
                key={index}
                className={`bg-slate-900/80 border rounded-xl p-3 font-mono text-xs transition-all ${
                  index === 0 && isGlowing
                    ? 'border-rose-500/60 bg-rose-950/20'
                    : isBlocklisted
                    ? 'border-purple-500/40 bg-purple-950/20 hover:border-purple-500/70'
                    : 'border-rose-500/30 hover:border-rose-500/60'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  {/* Truncated Session Token */}
                  <div className="flex items-center space-x-1.5 font-bold">
                    <Key className={`w-3.5 h-3.5 ${isBlocklisted ? 'text-purple-400' : 'text-rose-400'}`} />
                    <span className={isBlocklisted ? 'text-purple-300' : 'text-rose-400'}>{item.token_hash}</span>
                    <span className={`px-1.5 py-0.5 text-[9px] uppercase font-extrabold rounded border ${
                      isBlocklisted
                        ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                        : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                    }`}>
                      {isBlocklisted ? 'BLOCKLISTED' : '2-STRIKES KILLED'}
                    </span>
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
                    <span className={isBlocklisted ? 'text-purple-400 font-bold' : 'text-rose-400 font-bold'}>
                      RISK SCORE: {item.risk_score !== null && item.risk_score !== undefined ? item.risk_score : 'N/A (UNSCORED)'}
                    </span>
                  </div>
                  <div className={`font-semibold truncate ${isBlocklisted ? 'text-purple-200' : 'text-rose-300'}`} title={item.path}>
                    {item.path}
                  </div>
                  <div className="text-slate-400 text-[10px] pt-0.5 flex justify-between">
                    <span>SOURCE IP: {item.ip}</span>
                    <span className={isBlocklisted ? 'text-purple-400 font-semibold' : 'text-rose-400 font-semibold'}>
                      {isBlocklisted ? 'PRE-CHECK BLOCKED (403)' : 'ACTION: TERMINATED (403)'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

    </div>
  );
}
