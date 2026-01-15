
import React, { useRef, useEffect } from 'react';
import { MachineState, PinConfig, SimulationConfig } from '../types';
import { Play, Square, RefreshCw, Wind, ArrowDownToLine, MoveVertical, ExternalLink, CloudFog, Wifi, Settings, Fan, UploadCloud, Activity, Cloud, ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Home, Save } from 'lucide-react';

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
  smokeRunning: boolean;
  onSmokeControl: (action: 'start' | 'stop' | 'test') => void;
  onMotorStep?: (direction: 'up' | 'down' | 'left' | 'right' | 'both_forward' | 'both_backward' | 'motor_a_forward' | 'motor_a_backward' | 'motor_b_forward' | 'motor_b_backward', steps?: number) => void;
  onMotorContinuous?: (action: 'start' | 'stop', direction?: 'up' | 'down') => void;
  onMotorHome?: () => void;
  onSaveMotorPosition?: (state: 'DIP' | 'OPEN' | 'CLOSE') => void;
  motorAPosition?: number;
  motorBPosition?: number;
  fanRunning?: boolean;
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
  isOnline,
  smokeRunning,
  onSmokeControl,
  onMotorStep,
  onMotorContinuous,
  onMotorHome,
  onSaveMotorPosition,
  motorAPosition = 0,
  motorBPosition = 0,
  fanRunning = false
}) => {
  
  const StateBadge = ({ state, active }: { state: string, active: boolean }) => (
    <div className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${active ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/50' : 'bg-slate-800 text-slate-500 border border-slate-700'}`}>
      {state}
    </div>
  );

  const handleConfigChange = async (key: keyof SimulationConfig, value: string | boolean) => {
    const newConfig = { ...config };
    if (typeof value === 'boolean') {
      newConfig[key] = value;
    } else {
      const num = parseFloat(value);
      if (!isNaN(num)) {
        newConfig[key] = num;
      }
    }
    setConfig(newConfig);
    
    // Sync critical config changes immediately to server
    if (isOnline && piIp) {
      try {
        if (key === 'fanSpeed' && fanRunning) {
          // Fan speed changed and fan is running - update immediately
          await fetch(`http://${piIp}:8080/update_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fanSpeed: newConfig.fanSpeed }),
          });
        } else if (key === 'fanEnabled') {
          // Fan enabled/disabled - sync immediately so BLOW button works
          await fetch(`http://${piIp}:8080/update_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fanEnabled: newConfig.fanEnabled }),
          });
        }
      } catch (e) {
        console.error(`Failed to update ${key}:`, e);
      }
    }
  };

  // Clean up on unmount
  useEffect(() => {
    return () => {
      // Stop continuous movement when component unmounts
      if (onMotorContinuous) {
        onMotorContinuous('stop');
      }
    };
  }, [onMotorContinuous]);

  const startContinuousStep = (direction: 'up' | 'down') => {
    if (!onMotorContinuous || isRunning || !isOnline) return;
    onMotorContinuous('start', direction);
  };

  const stopContinuousStep = () => {
    if (!onMotorContinuous) return;
    onMotorContinuous('stop');
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

        {/* Loop Wait Times */}
        <div className="col-span-2 space-y-3 mt-2 p-3 bg-slate-950 border border-slate-800 rounded">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-tighter">Loop Wait Times</h4>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Open → Close</span>
                <span className="text-blue-400 font-mono">{config.waitAfterOpen}s</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="10" 
                step="0.1"
                value={config.waitAfterOpen} 
                onChange={(e) => handleConfigChange('waitAfterOpen', e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
            
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Close → Dip</span>
                <span className="text-blue-400 font-mono">{config.waitAfterClose}s</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="10" 
                step="0.1"
                value={config.waitAfterClose} 
                onChange={(e) => handleConfigChange('waitAfterClose', e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
            
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1">
                <span>Dip → Open</span>
                <span className="text-blue-400 font-mono">{config.waitAfterDip}s</span>
              </div>
              <input 
                type="range" 
                min="0" 
                max="10" 
                step="0.1"
                value={config.waitAfterDip} 
                onChange={(e) => handleConfigChange('waitAfterDip', e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
          </div>
        </div>

        <div className="text-xs text-slate-500 col-span-2 text-center my-2 border-b border-slate-800 leading-[0.1em]">
          <span className="bg-slate-900 px-2 uppercase tracking-widest font-bold">Manual Overrides</span>
        </div>

        <div className="col-span-2 flex items-center gap-2">
          <button 
            disabled={isRunning}
            onClick={() => onManualState(MachineState.DIP)}
            className="flex-1 p-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 text-sm flex items-center justify-center gap-2 border border-slate-700 transition-all active:scale-95"
          >
            <ArrowDownToLine size={16} /> Dip (Soap)
          </button>
          {onSaveMotorPosition && (
            <button
              disabled={isRunning || !isOnline}
              onClick={() => onSaveMotorPosition('DIP')}
              className="p-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white border border-emerald-700 transition-all active:scale-95"
              title="Save current position as DIP target"
            >
              <Save size={14} />
            </button>
          )}
        </div>

        <button 
          disabled={isRunning}
          onClick={() => onManualState(MachineState.BLOW)}
          className="col-span-2 p-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 text-sm flex items-center justify-center gap-2 border border-slate-700 transition-all active:scale-95"
        >
          <Wind size={16} /> Blow
        </button>

        <div className="col-span-2 flex items-center gap-2">
          <button 
            disabled={isRunning}
            onClick={() => onManualState(MachineState.CLOSE)}
            className="flex-1 p-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 text-sm flex items-center justify-center gap-2 border border-slate-700 transition-all active:scale-95"
          >
            <MoveVertical size={16} /> Close Arms
          </button>
          {onSaveMotorPosition && (
            <button
              disabled={isRunning || !isOnline}
              onClick={() => onSaveMotorPosition('CLOSE')}
              className="p-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white border border-emerald-700 transition-all active:scale-95"
              title="Save current position as CLOSE target"
            >
              <Save size={14} />
            </button>
          )}
        </div>

        <div className="col-span-2 flex items-center gap-2">
          <button 
            disabled={isRunning}
            onClick={() => onManualState(MachineState.OPEN)}
            className="flex-1 p-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 text-sm flex items-center justify-center gap-2 border border-slate-700 transition-all active:scale-95"
          >
            <ExternalLink size={16} /> Open Arms (Home)
          </button>
          {onSaveMotorPosition && (
            <button
              disabled={isRunning || !isOnline}
              onClick={() => onSaveMotorPosition('OPEN')}
              className="p-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white border border-emerald-700 transition-all active:scale-95"
              title="Save current position as OPEN target"
            >
              <Save size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Fine Motor Control - Arrow Keys */}
      {onMotorStep && (
        <div className="mt-3">
          <div className="text-xs text-slate-500 text-center mb-2 border-b border-slate-800 leading-[0.1em]">
            <span className="bg-slate-900 px-2 uppercase tracking-widest font-bold">Fine Motor Control</span>
          </div>
          
          {/* Continuous movement - Both motors */}
          <div className="flex justify-center gap-1 mb-3">
            <button
              disabled={isRunning || !isOnline}
              onMouseDown={() => startContinuousStep('up')}
              onMouseUp={stopContinuousStep}
              onMouseLeave={stopContinuousStep}
              onTouchStart={() => startContinuousStep('up')}
              onTouchEnd={stopContinuousStep}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 border border-slate-700 transition-all active:scale-95 select-none"
              title="Hold: Both motors up"
            >
              <ArrowUp size={16} />
            </button>
            <button
              disabled={isRunning || !isOnline}
              onMouseDown={() => startContinuousStep('down')}
              onMouseUp={stopContinuousStep}
              onMouseLeave={stopContinuousStep}
              onTouchStart={() => startContinuousStep('down')}
              onTouchEnd={stopContinuousStep}
              className="p-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 border border-slate-700 transition-all active:scale-95 select-none"
              title="Hold: Both motors down"
            >
              <ArrowDown size={16} />
            </button>
          </div>
          
          {/* Calibrate/Home button */}
          {onMotorHome && (
            <div className="flex justify-center mb-3">
              <button
                disabled={isRunning || !isOnline}
                onClick={onMotorHome}
                className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs font-bold text-white flex items-center gap-1.5 transition-all active:scale-95 border border-amber-700"
                title="Set current position as home (0, 0)"
              >
                <Home size={12} />
                Set Home
              </button>
            </div>
          )}
          
          {/* Individual motor controls */}
          <div className="space-y-2">
            {/* Motor A */}
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] text-slate-400 uppercase font-bold w-12">Motor A</span>
              <div className="flex items-center gap-1 flex-1">
                <button
                  disabled={isRunning || !isOnline}
                  onClick={() => onMotorStep('motor_a_backward', 5)}
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 border border-slate-700 transition-all active:scale-95"
                  title="5 steps backward"
                >
                  <ArrowLeft size={14} />
                </button>
                <span className="text-[9px] text-slate-600 font-mono w-6 text-center">5</span>
                <button
                  disabled={isRunning || !isOnline}
                  onClick={() => onMotorStep('motor_a_forward', 5)}
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 border border-slate-700 transition-all active:scale-95"
                  title="5 steps forward"
                >
                  <ArrowRight size={14} />
                </button>
                <span className="text-[9px] text-blue-400 font-mono ml-1 min-w-[50px] text-right">Pos: {motorAPosition}</span>
              </div>
            </div>
            
            {/* Motor B */}
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] text-slate-400 uppercase font-bold w-12">Motor B</span>
              <div className="flex items-center gap-1 flex-1">
                <button
                  disabled={isRunning || !isOnline}
                  onClick={() => onMotorStep('motor_b_backward', 5)}
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 border border-slate-700 transition-all active:scale-95"
                  title="5 steps backward"
                >
                  <ArrowLeft size={14} />
                </button>
                <span className="text-[9px] text-slate-600 font-mono w-6 text-center">5</span>
                <button
                  disabled={isRunning || !isOnline}
                  onClick={() => onMotorStep('motor_b_forward', 5)}
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-slate-200 border border-slate-700 transition-all active:scale-95"
                  title="5 steps forward"
                >
                  <ArrowRight size={14} />
                </button>
                <span className="text-[9px] text-blue-400 font-mono ml-1 min-w-[50px] text-right">Pos: {motorBPosition}</span>
              </div>
            </div>
          </div>
        </div>
      )}

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
              <Fan size={14} className={fanRunning ? "text-blue-400 animate-pulse" : (config.fanEnabled ? "text-blue-600" : "text-slate-600")} />
              <span className="text-xs text-slate-300 font-medium">Fan Enabled</span>
              {fanRunning && (
                <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-[9px] font-bold rounded border border-blue-500/30 animate-pulse">
                  BLOWING
                </span>
              )}
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
              <div className="flex justify-between text-xs mb-1">
                 <span className={`flex items-center gap-1 ${fanRunning ? 'text-blue-400 font-bold' : 'text-slate-400'}`}>
                   <Fan size={12} className={fanRunning ? "animate-spin" : ""}/> Fan Power
                 </span>
                 <span className={`font-mono ${fanRunning ? 'text-blue-400 font-bold' : 'text-blue-400'}`}>{config.fanSpeed}%</span>
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

          <div className="flex items-center justify-between p-2 bg-slate-950 border border-slate-800 rounded">
            <div className="flex items-center gap-2">
              <Cloud size={14} className={config.smokeEnabled ? "text-red-400" : "text-slate-600"} />
              <span className="text-xs text-slate-300 font-medium">Smoke Enabled</span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={config.smokeEnabled}
                onChange={(e) => handleConfigChange('smokeEnabled', e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-red-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
            </label>
          </div>

          {config.smokeEnabled && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => onSmokeControl('test')}
                  disabled={!isOnline || smokeRunning}
                  className="px-3 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs font-bold text-white flex items-center justify-center gap-1 transition-all"
                >
                  <Cloud size={12} /> Test
                </button>
                <button
                  onClick={() => onSmokeControl(smokeRunning ? 'stop' : 'start')}
                  disabled={!isOnline}
                  className={`px-3 py-2 rounded text-xs font-bold text-white flex items-center justify-center gap-1 transition-all ${
                    smokeRunning 
                      ? 'bg-red-700 hover:bg-red-600' 
                      : 'bg-emerald-600 hover:bg-emerald-500'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {smokeRunning ? <Square size={12} /> : <Play size={12} />}
                  {smokeRunning ? 'Stop' : 'Start'}
                </button>
              </div>
              
              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span className="flex items-center gap-1"><Cloud size={12}/> Intensity</span>
                  <span className="text-red-400 font-mono">{config.smokeIntensity}/127</span>
                </div>
                <input 
                  type="range" 
                  min="0" 
                  max="127" 
                  value={config.smokeIntensity} 
                  onChange={(e) => handleConfigChange('smokeIntensity', e.target.value)}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-500"
                />
              </div>
              
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Duration (s)</label>
                <input 
                  type="number" 
                  step="0.1"
                  min="0.1"
                  max="30"
                  value={config.smokeDuration}
                  onChange={(e) => handleConfigChange('smokeDuration', e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-red-500"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
