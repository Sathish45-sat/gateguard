import React from 'react';
import { Shield, Play, Pause, RefreshCw, Volume2, VolumeX, Zap, Wifi, WifiOff } from 'lucide-react';

export default function Header({ 
  isConnected, 
  isPolling, 
  setIsPolling, 
  onRefresh, 
  proxyUrl, 
  lastFetchTime,
  soundEnabled,
  setSoundEnabled,
  onSimulateKill
}) {
  return (
    <header className="soc-card border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-6 py-4 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        
        {/* Brand & SOC Indicator */}
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className={`w-10 h-10 rounded-lg bg-slate-900 border flex items-center justify-center transition-colors ${
              isConnected 
                ? 'border-cyan-500/50 text-cyan-400 soc-glow-cyan' 
                : 'border-rose-500/50 text-rose-400 soc-glow-rose'
            }`}>
              <Shield className="w-6 h-6" />
            </div>
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                isConnected ? 'bg-cyan-400' : 'bg-rose-400'
              }`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 ${
                isConnected ? 'bg-cyan-500' : 'bg-rose-500'
              }`}></span>
            </span>
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-white font-mono">
                Gate<span className="text-cyan-400">Guard</span>
              </h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">
                LIVE SOC v1.0
              </span>
            </div>
            <p className="text-xs text-slate-400 flex items-center space-x-2">
              <span>Proxy URL: <code className="text-cyan-300 font-mono">{proxyUrl}</code></span>
            </p>
          </div>
        </div>

        {/* Controls: Sound Toggle, Demo Trigger, Polling & Connection Status */}
        <div className="flex flex-wrap items-center gap-3">
          
          {/* Audio Alert Toggle (Default OFF) */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold transition-all ${
              soundEnabled
                ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 soc-glow-amber'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title={soundEnabled ? 'Audio Cue: ON (Mute audio)' : 'Audio Cue: OFF (Enable demo sound)'}
          >
            {soundEnabled ? (
              <>
                <Volume2 className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
                <span>SOUND ON</span>
              </>
            ) : (
              <>
                <VolumeX className="w-3.5 h-3.5 text-slate-500" />
                <span>SOUND OFF</span>
              </>
            )}
          </button>

          {/* Simulate Kill Demo Trigger */}
          {onSimulateKill && (
            <button
              onClick={onSimulateKill}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-rose-500/50 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs font-mono font-bold transition-all soc-glow-rose hover:scale-105 active:scale-95"
              title="Trigger a simulated session kill money shot for live demo audience"
            >
              <Zap className="w-3.5 h-3.5 text-rose-400 animate-bounce" />
              <span>SIMULATE KILL</span>
            </button>
          )}

          {/* Connection Badge */}
          <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-semibold transition-all ${
            isConnected
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 soc-glow-emerald'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400 soc-glow-rose'
          }`}>
            {isConnected ? (
              <>
                <Wifi className="w-3.5 h-3.5 animate-pulse" />
                <span>CONNECTED</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5" />
                <span>DISCONNECTED</span>
              </>
            )}
          </div>

          {/* Polling & Refresh Controls */}
          <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 rounded-lg p-1">
            <button
              onClick={() => setIsPolling(!isPolling)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-xs font-semibold font-mono transition-all ${
                isPolling
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 soc-glow-cyan'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
              title={isPolling ? 'Pause 2s polling' : 'Resume 2s polling'}
            >
              {isPolling ? (
                <>
                  <Pause className="w-3.5 h-3.5" />
                  <span>POLLING (2s)</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5" />
                  <span>PAUSED</span>
                </>
              )}
            </button>

            <button
              onClick={onRefresh}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors font-mono"
              title="Trigger immediate fetch /logs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>FETCH NOW</span>
            </button>
          </div>

        </div>

      </div>
    </header>
  );
}

