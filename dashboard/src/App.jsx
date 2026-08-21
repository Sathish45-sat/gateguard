import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import StatCards from './components/StatCards';
import RiskGauge from './components/RiskGauge';
import TrafficTable from './components/TrafficTable';
import KilledSessions from './components/KilledSessions';
import { Skull, X, AlertOctagon, ShieldX } from 'lucide-react';

// Easily configurable Proxy Base URL via Vite Environment Variable
const PROXY_URL = import.meta.env.VITE_PROXY_URL || 'http://localhost:8080';

/**
 * Web Audio API synthesizer for the kill-moment alert sound cue.
 * Self-contained, zero external asset dependencies.
 */
function playKillSoundCue() {
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();

    // Pulse 1: High warning tone (sawtooth frequency drop)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sawtooth';
    osc1.frequency.setValueAtTime(880, ctx.currentTime);
    osc1.frequency.exponentialRampToValueAtTime(220, ctx.currentTime + 0.25);
    gain1.gain.setValueAtTime(0.35, ctx.currentTime);
    gain1.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start();
    osc1.stop(ctx.currentTime + 0.25);

    // Pulse 2: Staccato alarm tone after 120ms
    setTimeout(() => {
      try {
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = 'sawtooth';
        osc2.frequency.setValueAtTime(987.77, ctx.currentTime);
        osc2.frequency.exponentialRampToValueAtTime(110, ctx.currentTime + 0.3);
        gain2.gain.setValueAtTime(0.35, ctx.currentTime);
        gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.start();
        osc2.stop(ctx.currentTime + 0.3);
      } catch (e) {}
    }, 120);
  } catch (err) {
    console.warn('Audio playback prevented or unsupported:', err);
  }
}

export default function App() {
  const [logs, setLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isPolling, setIsPolling] = useState(true);
  const [lastFetchTime, setLastFetchTime] = useState(null);

  // --- DEMO MONEY SHOT STATES ---
  const [recentlyKilledTokens, setRecentlyKilledTokens] = useState(new Set());
  const [killedPanelGlowing, setKilledPanelGlowing] = useState(false);
  const [killAlerts, setKillAlerts] = useState([]);
  const [soundEnabled, setSoundEnabled] = useState(false); // Default OFF for demo room safety

  // Refs for tracking diffs across 2-second polls
  const seenKilledTokensRef = useRef(new Set()); // Set of token hashes that already fired a kill alert
  const hasInitializedRef = useRef(false);

  /**
   * Triggers the full high-impact visual event ("money shot") for a newly killed session
   */
  const triggerKillMoment = useCallback((killedLog) => {
    const tokenHash = killedLog.token_hash;

    // 1. Highlight newly killed row in Traffic Table (active for 5s)
    setRecentlyKilledTokens((prev) => {
      const next = new Set(prev);
      next.add(tokenHash);
      return next;
    });

    setTimeout(() => {
      setRecentlyKilledTokens((prev) => {
        const next = new Set(prev);
        next.delete(tokenHash);
        return next;
      });
    }, 5000);

    // 2. Pulse border glow on Killed Sessions Panel (active for exactly 3 pulses = 2.4s)
    setKilledPanelGlowing(true);
    setTimeout(() => {
      setKilledPanelGlowing(false);
    }, 2400);

    // 3. Add Toast/Banner notification
    const alertId = `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`;
    const isBlocklisted = killedLog.status === 'blocklisted';
    const newAlert = {
      id: alertId,
      token_hash: tokenHash,
      risk_score: killedLog.risk_score !== null && killedLog.risk_score !== undefined ? killedLog.risk_score : 'N/A',
      status: killedLog.status || 'killed',
      path: killedLog.path || '/search?q=UNION+SELECT',
      ip: killedLog.ip || '127.0.0.1',
      timestamp: killedLog.timestamp || new Date().toISOString(),
      strikes: isBlocklisted ? 'PRE-CHECK' : 2
    };

    setKillAlerts((prev) => [newAlert, ...prev.slice(0, 2)]); // Keep max 3 active alerts

    // Auto-dismiss toast after 4.5 seconds
    setTimeout(() => {
      setKillAlerts((prev) => prev.filter((a) => a.id !== alertId));
    }, 4500);

    // 4. Play audio cue if enabled by user
    if (soundEnabled) {
      playKillSoundCue();
    }
  }, [soundEnabled]);

  /**
   * Poll GET /logs from the proxy service and perform token_hash + status diffing
   */
  const fetchLogs = useCallback(async () => {
    try {
      const response = await fetch(`${PROXY_URL}/logs`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (Array.isArray(data)) {
        // Adapt incoming logs to standard contract matching GateGuard Go proxy /logs endpoint
        const parsedLogs = data.map((item) => {
          const tier = item.tier || item.status || (
            typeof item.risk_score === 'number'
              ? (item.risk_score > 85 ? 'killed' : item.risk_score > 65 ? 'challenged' : item.risk_score > 30 ? 'suspicious' : 'clean')
              : 'clean'
          );

          const tokenHash = item.session_token_hash || item.token_hash || item.token || item.session_token || item.session_id || 'anon';
          const riskScore = typeof item.risk_score === 'number' ? item.risk_score : (item.risk_score === null ? null : (typeof item.score === 'number' ? item.score : null));

          return {
            timestamp: item.timestamp || new Date().toISOString(),
            ip: item.ip || item.client_ip || item.source_ip || '127.0.0.1',
            path: item.path || item.url || item.request_uri || '/',
            risk_score: riskScore,
            status: tier, // Preserve all 5 tier values: clean, challenged, suspicious, killed, blocklisted
            token_hash: tokenHash,
            action: item.action || 'forwarded'
          };
        });

        // Sort newest logs first
        parsedLogs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        const currentBatch = parsedLogs.slice(0, 50);

        // --- DIFF LOGIC: Trigger alert ONCE per newly killed token ---
        const newlyKilledSessions = [];

        currentBatch.forEach((log) => {
          if (log.status === 'killed' || log.status === 'blocklisted') {
            if (!seenKilledTokensRef.current.has(log.token_hash)) {
              seenKilledTokensRef.current.add(log.token_hash);
              if (hasInitializedRef.current) {
                newlyKilledSessions.push(log);
              }
            }
          }
        });

        // Fire money shot only for newly identified killed sessions
        if (hasInitializedRef.current && newlyKilledSessions.length > 0) {
          newlyKilledSessions.forEach((killedItem) => triggerKillMoment(killedItem));
        }

        // Set initialized flag after first successful fetch
        if (!hasInitializedRef.current) {
          hasInitializedRef.current = true;
        }

        setLogs(currentBatch);
        setIsConnected(true);
        setLastFetchTime(new Date().toISOString());
      }
    } catch (err) {
      setIsConnected(false);
    }
  }, [triggerKillMoment]);

  // Set up 2-second polling timer
  useEffect(() => {
    if (!isPolling) return;

    fetchLogs(); // Immediate fetch on mount or resume
    const interval = setInterval(fetchLogs, 2000);

    return () => clearInterval(interval);
  }, [isPolling, fetchLogs]);

  /**
   * Helper to simulate a session kill money shot on demand during live demos
   */
  const handleSimulateKill = () => {
    const fakeToken = `tok_${Math.random().toString(36).substring(2, 8)}${Math.random().toString(36).substring(2, 6)}`;
    const fakePaths = [
      '/search?q=UNION+SELECT+1,2,username,password+FROM+users',
      '/search?q=%27+OR+%271%27%3D%271%27+--',
      '/search?q=cmd.exe+%2Fc+dir+C%3A%5C',
      '/search?q=%3Cscript%3Ealert%28document.cookie%29%3C%2Fscript%3E'
    ];
    const fakeIps = ['185.220.101.5', '198.51.100.42', '45.33.21.90', '203.0.113.19'];
    
    const simulatedLog = {
      timestamp: new Date().toISOString(),
      ip: fakeIps[Math.floor(Math.random() * fakeIps.length)],
      path: fakePaths[Math.floor(Math.random() * fakePaths.length)],
      risk_score: Math.floor(Math.random() * 20) + 80,
      status: 'killed',
      token_hash: fakeToken
    };

    // Prepend to logs & trigger diff map update + money shot
    setLogs((prev) => [simulatedLog, ...prev.slice(0, 49)]);
    prevStatusMapRef.current.set(fakeToken, 'killed');
    triggerKillMoment(simulatedLog);
  };

  const removeAlert = (id) => {
    setKillAlerts((prev) => prev.filter((alert) => alert.id !== id));
  };

  // Derived properties
  const latestLog = logs[0] || null;
  const killedCount = logs.filter((l) => l.status === 'killed' || l.status === 'blocklisted').length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans relative overflow-x-hidden">
      
      {/* --- REFINED DEMO KILL-EVENT TOAST / BANNER NOTIFICATIONS --- */}
      <div className="fixed top-20 right-4 left-4 sm:left-auto sm:right-6 z-50 flex flex-col space-y-3 max-w-md pointer-events-none">
        {killAlerts.map((alert) => (
          <div
            key={alert.id}
            className="pointer-events-auto bg-slate-900/95 border border-rose-500/50 rounded-xl p-4 shadow-xl text-rose-100 font-mono backdrop-blur-xl flex items-start justify-between gap-3 border-l-4 border-l-rose-500 transition-all duration-300"
          >
            <div className="flex items-start space-x-3">
              <div className="p-2 rounded-lg bg-rose-500/20 text-rose-400 border border-rose-500/30 shrink-0 mt-0.5">
                <Skull className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                    {alert.status === 'blocklisted' ? 'PRE-CHECK BLOCK' : 'SESSION REVOKED'}
                  </span>
                  <span className="text-xs text-slate-400">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <h4 className="text-sm font-bold text-white tracking-wide flex items-center gap-1.5">
                  <span>Session <code className="bg-slate-950 px-1.5 py-0.5 rounded text-rose-300 border border-rose-500/30">{alert.token_hash}</code> {alert.status === 'blocklisted' ? 'BLOCKED' : 'KILLED'}</span>
                </h4>

                <p className="text-xs text-slate-300">
                  Trigger: <span className="font-semibold text-rose-300">{alert.status === 'blocklisted' ? 'Blocklist Pre-check' : 'Two-Strike Limit'}</span> | Score: <span className="font-semibold text-rose-300">{alert.risk_score}</span>
                </p>

                <div className="text-[11px] text-slate-400 bg-slate-950/70 p-2 rounded border border-slate-800 font-mono space-y-0.5 mt-1">
                  <div className="truncate max-w-xs" title={alert.path}>
                    <span className="text-slate-500">PATH: </span>
                    <span className="text-slate-300">{alert.path}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">IP: </span>
                    <span className="text-slate-300">{alert.ip}</span>
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={() => removeAlert(alert.id)}
              className="text-slate-500 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition-colors shrink-0"
              title="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Header Navigation */}
      <Header
        isConnected={isConnected}
        isPolling={isPolling}
        setIsPolling={setIsPolling}
        onRefresh={fetchLogs}
        proxyUrl={PROXY_URL}
        lastFetchTime={lastFetchTime}
        soundEnabled={soundEnabled}
        setSoundEnabled={setSoundEnabled}
        onSimulateKill={handleSimulateKill}
      />

      {/* Main Content Dashboard Layout */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 w-full space-y-6">
        
        {/* Disconnected Alert Banner */}
        {!isConnected && (
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 text-rose-300 flex flex-col md:flex-row md:items-center justify-between gap-3 font-mono text-xs soc-glow-rose">
            <div className="flex items-center space-x-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-rose-500"></span>
              </span>
              <span className="font-bold uppercase">PROXY DISCONNECTED:</span>
              <span>
                Unable to reach <code className="bg-slate-900 px-1.5 py-0.5 rounded text-cyan-300 font-semibold">{PROXY_URL}/logs</code>. Polling automatically every 2s...
              </span>
            </div>
            <button
              onClick={fetchLogs}
              className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 border border-rose-500/40 rounded transition-colors font-bold uppercase self-start md:self-auto"
            >
              RETRY NOW
            </button>
          </div>
        )}

        {/* KPI Stat Cards */}
        <StatCards logs={logs} killedCount={killedCount} />

        {/* Middle Section: Live Risk Gauge + Killed Sessions */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7">
            <RiskGauge latestLog={latestLog} />
          </div>
          <div className="lg:col-span-5">
            <KilledSessions logs={logs} isGlowing={killedPanelGlowing} />
          </div>
        </div>

        {/* Bottom Section: Traffic Log Table */}
        <div>
          <TrafficTable logs={logs} recentlyKilledTokens={recentlyKilledTokens} />
        </div>

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 px-6 text-center text-xs font-mono text-slate-500">
        GateGuard SOC Security Dashboard — Target Proxy: {PROXY_URL}
      </footer>
    </div>
  );
}
