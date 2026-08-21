import React from 'react';
import { Shield, ShieldAlert, ShieldCheck, Skull, Terminal, Key, Clock, Ban } from 'lucide-react';

export default function RiskGauge({ latestLog }) {
  if (!latestLog) {
    return (
      <div className="soc-card rounded-2xl p-6 flex items-center justify-center h-full min-h-[280px]">
        <span className="text-slate-500 font-mono text-sm">No incoming request traffic...</span>
      </div>
    );
  }

  const { risk_score, status, path, ip, timestamp, token_hash } = latestLog;

  // Determine color scheme based on risk score / status
  let colorTheme = {
    text: 'text-emerald-400',
    stroke: '#10b981',
    glow: 'soc-glow-emerald',
    badgeBg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    label: 'LOW RISK (CLEAN)',
    icon: ShieldCheck
  };

  if (status === 'challenged') {
    colorTheme = {
      text: 'text-cyan-400',
      stroke: '#06b6d4',
      glow: 'soc-glow-cyan',
      badgeBg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
      label: 'CHALLENGED (DELAY)',
      icon: Clock
    };
  } else if (status === 'suspicious') {
    colorTheme = {
      text: 'text-amber-400',
      stroke: '#f59e0b',
      glow: 'soc-glow-amber',
      badgeBg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      label: 'STRIKE 1 (SUSPICIOUS)',
      icon: ShieldAlert
    };
  } else if (status === 'killed') {
    colorTheme = {
      text: 'text-rose-400',
      stroke: '#f43f5e',
      glow: 'soc-glow-rose',
      badgeBg: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
      label: 'STRIKE 2 (KILLED)',
      icon: Skull
    };
  } else if (status === 'blocklisted') {
    colorTheme = {
      text: 'text-purple-400',
      stroke: '#a855f7',
      glow: 'soc-glow-purple',
      badgeBg: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
      label: 'BLOCKLISTED (PRE-CHECK)',
      icon: Ban
    };
  }

  // SVG Gauge radial progress math (radius = 68, circumference = 2 * PI * 68 = 427.26)
  const radius = 68;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const scoreNum = typeof risk_score === 'number' ? risk_score : (status === 'blocklisted' ? 100 : 0);
  const strokeDashoffset = circumference - (scoreNum / 100) * circumference;

  const StatusIcon = colorTheme.icon;

  return (
    <div className={`soc-card rounded-2xl p-6 ${colorTheme.glow} transition-all duration-500 relative overflow-hidden flex flex-col justify-between`}>
      
      {/* Background SOC Ambient Grid */}
      <div className="absolute inset-0 opacity-5 pointer-events-none bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:16px_16px]"></div>

      {/* Header Title */}
      <div className="flex items-center justify-between z-10">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-bold text-slate-300 uppercase tracking-widest font-mono">
            LIVE REQUEST SCORE GAUGE
          </h2>
        </div>
        <div className={`px-2.5 py-1 rounded-md border text-[11px] font-bold font-mono uppercase flex items-center space-x-1.5 ${colorTheme.badgeBg}`}>
          <StatusIcon className="w-3.5 h-3.5" />
          <span>{colorTheme.label}</span>
        </div>
      </div>

      {/* Gauge Visualization Section */}
      <div className="my-4 flex flex-col md:flex-row items-center justify-around gap-6 z-10">
        
        {/* Radial SVG Gauge */}
        <div className="relative w-44 h-44 flex items-center justify-center">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 160 160">
            {/* Background Track */}
            <circle
              cx="80"
              cy="80"
              r={radius}
              stroke="#1e293b"
              strokeWidth={strokeWidth}
              fill="transparent"
            />
            {/* Value Arc */}
            <circle
              cx="80"
              cy="80"
              r={radius}
              stroke={colorTheme.stroke}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="transparent"
              className="transition-all duration-700 ease-out"
            />
          </svg>

          {/* Centered Score Counter */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <span className={`text-4xl font-extrabold font-mono tracking-tight ${colorTheme.text}`}>
              {typeof risk_score === 'number' ? risk_score : 'N/A'}
            </span>
            <span className="text-[10px] text-slate-400 font-mono tracking-wider uppercase mt-0.5">
              {typeof risk_score === 'number' ? 'RISK SCORE' : 'PRE-CHECK BLOCKED'}
            </span>
          </div>
        </div>

        {/* Latest Request Meta Card */}
        <div className="flex-1 w-full bg-slate-900/80 border border-slate-800 rounded-xl p-4 font-mono text-xs space-y-2.5">
          <div className="flex justify-between items-center pb-2 border-b border-slate-800">
            <span className="text-slate-500 uppercase text-[10px] tracking-wider">LATEST TARGET PATH</span>
            <span className="text-slate-400 text-[11px]">
              {new Date(timestamp).toLocaleTimeString()}
            </span>
          </div>

          <div className="text-cyan-300 font-medium break-all text-sm bg-slate-950/60 p-2 rounded border border-slate-800/80">
            {path}
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1 text-slate-400">
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">SOURCE IP</span>
              <span className="text-slate-200 font-semibold">{ip}</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 block uppercase">SESSION TOKEN</span>
              <span className="text-slate-200 font-semibold flex items-center space-x-1">
                <Key className="w-3 h-3 text-cyan-400 inline" />
                <span>{token_hash}</span>
              </span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
