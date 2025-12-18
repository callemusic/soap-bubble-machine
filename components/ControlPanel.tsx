
import React from 'react';
import { MachineState, PinConfig, SimulationConfig } from '../types';
import { Play, Square, RefreshCw, Wind, ArrowDownToLine, MoveVertical, ExternalLink, CloudFog, Wifi, Settings, Fan, UploadCloud, Activity } from 'lucide-react';

interface ControlPanelProps {
  currentState: MachineState;
  isRunning: boolean;
  onToggleRun: () => void;
  onManualState: (state: MachineState) => void;
  pins: PinConfig;
  piIp: string;
  setPiIp: (ip: string) => void;
  config: SimulationConfig;
  setConfig: (config: SimulationConfig) => void;
  onSyncConfig: () => void;
  isSyncing: boolean;
  isOnline: boolean;
}

const ControlPanel: React.FC<ControlPanelProps> = ({ 
  currentState, 
  isRunning, 
  onToggleRun, 
  onManualState,
  pins,
  piIp,
  setPiIp,
  config,
  setConfig,
  onSyncConfig,
  isSyncing,
  isOnline
}) => {
  
  const StateBadge = ({ state, active }: { state: string, active: boolean }) => (
    <div className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${active ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/50' : 'bg-slate-800 text-slate-500 border border-slate-700'}`}>
      {state}
    </div>
  );

  const handleConfigChange = (key: keyof SimulationConfig, value: string | boolean) => {
    if (typeof value === 'boolean') {
      setConfig({ ...config, [key]: value });
    } else {
      const num = parseFloat(value);
      if (!isNaN(num)) {
        setConfig({ ...config, [key]: num });
      }
    }
  };

  return (
    <div className="p-6 flex flex-col gap-6">
      
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity className={`w-5 h-5 ${isOnline ? 'text-green-400 animate-pulse' : 'text-slate-600'}`} />
            Live Dashboard
          </h2>
          <p className="text-slate-400 text-sm mt-1">{isOnline ? 'Hardware Link Active' : 'Offline Simulation'}</p>
        </div>
        
        {/* Connection Settings */}
        <div className="flex flex-col items-end gap-1">
          <div className={`flex items-center gap-2 px-2 py-1 rounded border transition-colors ${isOnline ? 'bg-green-500/10 border-green-500/30' : 'bg-slate-950 border-slate-800'}`}>
             <Wifi size={14} className={isOnline ? "text-green-400" : "text-slate-600"} />
             <input 
               type="text" 
               placeholder="Pi IP..." 
               value={piIp}
               onChange={(e) => setPiIp(e.target.value)}
               className="bg-transparent text-xs text-slate-300 w-24 outline-none placeholder-slate-700"
             />
          </div>
          {isOnline && <span className="text-[10px] text-green-500 font-bold animate-pulse">● HEARTBEAT OK</span>}
        </div>
      </div>

      {/* Main Controls */}
      <div className="grid grid-cols-2 gap-4">
        <button 
          onClick={onToggleRun}
          className={`col-span-2 flex items-center justify-center gap-2 p-4 rounded-lg font-bold text-white transition-all ${isRunning ? 'bg-red-500 hover:bg-red-600' : 'bg-emerald-600 hover:bg-emerald-500'}`}
        >
          {isRunning ? <><Square size={18} fill="currentColor" /> STOP SEQUENCE</> : <><Play size={18} fill="currentColor" /> START LOOP</>}
        </button>

        <div className="text-xs text-slate-500 col-span-2 text-center my-2 border-b border-slate-800 leading-[0.1em]">
          <span className="bg-slate-900 px-2 uppercase tracking-widest font-bold">Manual Overrides</span>
        </div>

        <button 
          disabled={isRunning}
          onClick={() => onManualState(MachineState.DIP)}
          className="p-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 text-sm flex items-center justify-center gap-2 border border-slate-700 transition-all active:scale-95"
        >
          <ArrowDownToLine size={16} /> Dip (Soap)
        </button>

        <button 
          disabled={isRunning}
          onClick={() => onManualState(MachineState.BLOW)}
          className="p-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 text-sm flex items-center justify-center gap-2 border border-slate-700 transition-all active:scale-95"
        >
          <Wind size={16} /> Blow
        </button>

        <button 
          disabled={isRunning}
          onClick={() => onManualState(MachineState.CLOSE)}
          className="p-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 text-sm flex items-center justify-center gap-2 border border-slate-700 transition-all active:scale-95"
        >
          <MoveVertical size={16} /> Close Arms
        </button>

        <button 
          disabled={isRunning}
          onClick={() => onManualState(MachineState.OPEN)}
          className="p-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 text-sm flex items-center justify-center gap-2 border border-slate-700 transition-all active:scale-95"
        >
          <ExternalLink size={16} /> Open Arms
        </button>
      </div>

      {/* Configuration Section */}
      <div className="mt-6 border-t border-slate-800 pt-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <Settings size={14} /> Sequence Calibration
          </h3>
          <button 
            onClick={onSyncConfig}
            disabled={!isOnline || isSyncing}
            className="flex items-center gap-1.5 px-2 py-1 bg-blue-600 hover:bg-blue-500 rounded text-[10px] font-bold text-white uppercase tracking-wide transition-all disabled:opacity-40 disabled:bg-slate-700 disabled:cursor-not-allowed"
          >
            <UploadCloud size={12} />
            {isSyncing ? 'Syncing...' : 'Push to Pi'}
          </button>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-2 bg-slate-950 border border-slate-800 rounded">
            <div className="flex items-center gap-2">
              <Fan size={14} className={config.fanEnabled ? "text-blue-400" : "text-slate-600"} />
              <span className="text-xs text-slate-300 font-medium">Fan Enabled</span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.fanEnabled}
                onChange={(e) => handleConfigChange('fanEnabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>
          
          {config.fanEnabled && (
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                 <span className="flex items-center gap-1"><Fan size={12}/> Fan Power</span>
                 <span className="text-blue-400 font-mono">{config.fanSpeed}%</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={config.fanSpeed} 
                onChange={(e) => handleConfigChange('fanSpeed', e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
             <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Dip Wait</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={config.dipDuration}
                  onChange={(e) => handleConfigChange('dipDuration', e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                />
             </div>
             <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Lift Time</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={config.liftDuration}
                  onChange={(e) => handleConfigChange('liftDuration', e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                />
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
