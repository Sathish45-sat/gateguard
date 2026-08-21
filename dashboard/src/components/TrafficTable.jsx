import React, { useState } from 'react';
import { Search, Filter, ShieldCheck, AlertTriangle, Skull, Key, Server, Clock, Ban } from 'lucide-react';

export default function TrafficTable({ logs, recentlyKilledTokens = new Set() }) {
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Filter logs based on active filter button and search query string
  const filteredLogs = logs.filter((log) => {
    const matchesStatus = filterStatus === 'all' || log.status === filterStatus;
    const matchesSearch =
      searchTerm === '' ||
      log.path.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.ip.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.token_hash.toLowerCase().includes(searchTerm.toLowerCase());

    return matchesStatus && matchesSearch;
  });

  return (
    <div className="soc-card rounded-2xl p-6 flex flex-col h-full">
      
      {/* Table Top Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        
        {/* Title */}
        <div className="flex items-center space-x-2">
          <Server className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono">
            LIVE TRAFFIC INSPECTION LOGS ({filteredLogs.length})
          </h3>
        </div>

        {/* Filters and Search Bar */}
        <div className="flex flex-wrap items-center gap-2">
          
          {/* Status Filter Buttons (All 5 tiers preserved) */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1 font-mono text-xs overflow-x-auto">
            {['all', 'clean', 'challenged', 'suspicious', 'killed', 'blocklisted'].map((status) => (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                className={`px-2.5 py-1 rounded-md capitalize transition-all whitespace-nowrap ${
                  filterStatus === status
                    ? status === 'clean'
                      ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30'
                      : status === 'challenged'
                      ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30'
                      : status === 'suspicious'
                      ? 'bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30'
                      : status === 'killed'
                      ? 'bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30'
                      : status === 'blocklisted'
                      ? 'bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30'
                      : 'bg-slate-700 text-white font-bold border border-slate-600'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {status}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search path, IP, token..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 w-48 lg:w-60"
            />
          </div>

        </div>

      </div>

      {/* Table View */}
      <div className="overflow-x-auto overflow-y-auto max-h-[500px] border border-slate-800 rounded-xl bg-slate-950/60">
        <table className="w-full text-left border-collapse font-mono text-xs">
          <thead className="bg-slate-900/90 text-slate-400 uppercase text-[10px] tracking-wider sticky top-0 z-10 border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4">Source IP</th>
              <th className="py-3 px-4">Request Path</th>
              <th className="py-3 px-4">Risk Score</th>
              <th className="py-3 px-4">Status / Tier</th>
              <th className="py-3 px-4">Token Hash</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500 italic">
                  No request logs matching selected criteria.
                </td>
              </tr>
            ) : (
              filteredLogs.map((log, index) => {
                const isRecentlyKilled = (log.status === 'killed' || log.status === 'blocklisted') && recentlyKilledTokens.has(log.token_hash);
                
                let rowStyle = 'hover:bg-slate-900/60';
                let statusBadge = null;

                if (isRecentlyKilled) {
                  rowStyle = 'animate-kill-flash-3x border-l-4 border-l-rose-500 text-rose-100 font-medium z-10 relative';
                  statusBadge = (
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-rose-600 text-white border border-rose-400 shadow-[0_0_15px_rgba(244,63,94,0.7)] inline-flex items-center space-x-1.5 animate-pop-3x">
                      <Skull className="w-3.5 h-3.5 text-white" />
                      <span>{log.status === 'blocklisted' ? 'BLOCKED' : 'JUST KILLED'}</span>
                    </span>
                  );
                } else if (log.status === 'clean') {
                  rowStyle = 'bg-emerald-950/10 hover:bg-emerald-900/20 border-l-2 border-l-emerald-500/80';
                  statusBadge = (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 inline-flex items-center space-x-1">
                      <ShieldCheck className="w-3 h-3" />
                      <span>CLEAN</span>
                    </span>
                  );
                } else if (log.status === 'challenged') {
                  rowStyle = 'bg-cyan-950/15 hover:bg-cyan-900/25 border-l-2 border-l-cyan-500/80';
                  statusBadge = (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 inline-flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      <span>CHALLENGED</span>
                    </span>
                  );
                } else if (log.status === 'suspicious') {
                  rowStyle = 'bg-amber-950/15 hover:bg-amber-900/25 border-l-2 border-l-amber-500/80';
                  statusBadge = (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 inline-flex items-center space-x-1">
                      <AlertTriangle className="w-3 h-3" />
                      <span>SUSPICIOUS</span>
                    </span>
                  );
                } else if (log.status === 'killed') {
                  rowStyle = 'bg-rose-950/20 hover:bg-rose-900/30 border-l-2 border-l-rose-500/80';
                  statusBadge = (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 inline-flex items-center space-x-1">
                      <Skull className="w-3 h-3" />
                      <span>KILLED</span>
                    </span>
                  );
                } else if (log.status === 'blocklisted') {
                  rowStyle = 'bg-purple-950/20 hover:bg-purple-900/30 border-l-2 border-l-purple-500/80';
                  statusBadge = (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/30 inline-flex items-center space-x-1">
                      <Ban className="w-3 h-3" />
                      <span>BLOCKLISTED</span>
                    </span>
                  );
                }

                // Render risk score pill
                const isScoreNull = log.risk_score === null || log.risk_score === undefined;
                const scorePill = isScoreNull ? (
                  <span className="font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                    N/A
                  </span>
                ) : (
                  <span
                    className={`font-bold px-2 py-0.5 rounded ${
                      log.risk_score > 85
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : log.risk_score > 65
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                        : log.risk_score > 30
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {log.risk_score}
                  </span>
                );

                return (
                  <tr key={index} className={`transition-all duration-300 ${rowStyle}`}>
                    <td className="py-2.5 px-4 text-slate-400 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="py-2.5 px-4 font-semibold text-slate-300 whitespace-nowrap">
                      {log.ip}
                    </td>
                    <td className="py-2.5 px-4 text-cyan-300 max-w-xs truncate" title={log.path}>
                      {log.path}
                    </td>
                    <td className="py-2.5 px-4 whitespace-nowrap">
                      {scorePill}
                    </td>
                    <td className="py-2.5 px-4 whitespace-nowrap">{statusBadge}</td>
                    <td className="py-2.5 px-4 text-slate-400 whitespace-nowrap">
                      <span className="flex items-center space-x-1 text-slate-400">
                        <Key className="w-3 h-3 text-slate-500" />
                        <span className={isRecentlyKilled ? 'text-white font-extrabold' : ''}>{log.token_hash}</span>
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
}
