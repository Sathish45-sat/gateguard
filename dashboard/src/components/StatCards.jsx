import React from 'react';
import { Activity, ShieldCheck, AlertTriangle, Skull, Gauge } from 'lucide-react';

export default function StatCards({ logs, killedCount }) {
  const total = logs.length;
  const cleanCount = logs.filter(l => l.status === 'clean').length;
  const suspiciousCount = logs.filter(l => l.status === 'suspicious' || l.status === 'challenged').length;
  
  // Exclude null/unscored requests from average calculation
  const scoredLogs = logs.filter(l => typeof l.risk_score === 'number');
  const avgScore = scoredLogs.length > 0 
    ? Math.round(scoredLogs.reduce((acc, l) => acc + l.risk_score, 0) / scoredLogs.length) 
    : 0;

  const stats = [
    {
      title: 'TOTAL EVALUATED',
      value: total,
      icon: Activity,
      color: 'text-cyan-400',
      bg: 'bg-cyan-500/10',
      border: 'border-cyan-500/20'
    },
    {
      title: 'CLEAN TRAFFIC',
      value: cleanCount,
      subText: total > 0 ? `${Math.round((cleanCount / total) * 100)}%` : '0%',
      icon: ShieldCheck,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20'
    },
    {
      title: 'SUSPICIOUS / CHALLENGED',
      value: suspiciousCount,
      subText: total > 0 ? `${Math.round((suspiciousCount / total) * 100)}%` : '0%',
      icon: AlertTriangle,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20'
    },
    {
      title: 'KILLED & BLOCKED',
      value: killedCount,
      icon: Skull,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/20'
    },
    {
      title: 'AVG RISK SCORE',
      value: avgScore,
      subText: '/ 100',
      icon: Gauge,
      color: avgScore > 65 ? 'text-rose-400' : avgScore > 30 ? 'text-amber-400' : 'text-emerald-400',
      bg: avgScore > 65 ? 'bg-rose-500/10' : avgScore > 30 ? 'bg-amber-500/10' : 'bg-emerald-500/10',
      border: avgScore > 65 ? 'border-rose-500/20' : avgScore > 30 ? 'border-amber-500/20' : 'border-emerald-500/20'
    }
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
      {stats.map((stat, idx) => {
        const Icon = stat.icon;
        return (
          <div
            key={idx}
            className={`soc-card rounded-xl p-4 border ${stat.border} transition-transform hover:-translate-y-0.5`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold tracking-wider text-slate-400 font-mono">
                {stat.title}
              </span>
              <div className={`p-1.5 rounded-lg ${stat.bg} ${stat.color}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div className="mt-2 flex items-baseline space-x-2">
              <span className={`text-2xl font-extrabold font-mono ${stat.color}`}>
                {stat.value}
              </span>
              {stat.subText && (
                <span className="text-xs text-slate-400 font-mono">
                  {stat.subText}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
