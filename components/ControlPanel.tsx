
import React, { useState, useEffect } from 'react';
import { MachineState, PinConfig, SimulationConfig } from '../types';
import { Play, Square, RefreshCw, Wind, ArrowDownToLine, MoveVertical, ExternalLink, CloudFog, Wifi, Settings, Fan, UploadCloud, Activity, Zap, Rocket, ArrowLeft, ArrowRight, Home, Save } from 'lucide-react';

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
  hardwarePowered: boolean;
  setHardwarePowered: (powered: boolean) => void;
  fanRunning: boolean;
  onDeployServer: () => void;
}

interface MotorPositions {
  motorA: number;
  motorB: number;
  homeA: number;
  homeB: number;
  dipA?: number | null;
  dipB?: number | null;
  closeA?: number | null;
  closeB?: number | null;
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
  hardwarePowered,
  setHardwarePowered,
  fanRunning,
  onDeployServer
}) => {
  const [motorPositions, setMotorPositions] = useState<MotorPositions>({ motorA: 0, motorB: 0, homeA: 0, homeB: 0 });
  const [isTrimming, setIsTrimming] = useState(false);
  
  // Load motor positions from health check
  useEffect(() => {
    if (isOnline && piIp) {
      const loadPositions = async () => {
        try {
          const res = await fetch(`http://${piIp}:8080/get_motor_positions`);
          if (res.ok) {
            const data = await res.json();
            if (data.positions) {
              setMotorPositions(data.positions);
            }
          }
        } catch (e) {
          console.error("Failed to load motor positions:", e);
        }
      };
      loadPositions();
      const interval = setInterval(loadPositions, 2000);
      return () => clearInterval(interval);
    }
  }, [isOnline, piIp]);
  
  const trimMotor = async (motor: 'A' | 'B', direction: 'forward' | 'backward', steps: number = 10) => {
    if (!isOnline || isTrimming) return;
    setIsTrimming(true);
    try {
      const res = await fetch(`http://${piIp}:8080/trim_motor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motor, direction, steps }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.positions) {
          setMotorPositions(data.positions);
        }
      }
    } catch (e) {
      console.error("Failed to trim motor:", e);
    } finally {
      setIsTrimming(false);
    }
  };
  
  const saveHome = async () => {
    if (!isOnline) return;
    try {
      const res = await fetch(`http://${piIp}:8080/save_home`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.positions) {
          setMotorPositions(data.positions);
        }
        alert('✅ Home position saved!');
      }
    } catch (e) {
      console.error("Failed to save home:", e);
      alert('❌ Failed to save home position');
    }
  };
  
  const saveDip = async () => {
    if (!isOnline) return;
    try {
      const res = await fetch(`http://${piIp}:8080/save_dip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.positions) {
          setMotorPositions(data.positions);
        }
        alert('✅ DIP position saved!');
      }
    } catch (e) {
      console.error("Failed to save DIP:", e);
      alert('❌ Failed to save DIP position');
    }
  };
  
  const saveClose = async () => {
    if (!isOnline) return;
    try {
      const res = await fetch(`http://${piIp}:8080/save_close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.positions) {
          setMotorPositions(data.positions);
        }
        alert('✅ CLOSE position saved!');
      }
    } catch (e) {
      console.error("Failed to save CLOSE:", e);
      alert('❌ Failed to save CLOSE position');
    }
  };
  
  const returnToHome = async () => {
    if (!isOnline || isTrimming) return;
    setIsTrimming(true);
    try {
      const res = await fetch(`http://${piIp}:8080/return_home`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.positions) {
          setMotorPositions(data.positions);
        }
      }
    } catch (e) {
      console.error("Failed to return home:", e);
    } finally {
      setIsTrimming(false);
    }
  };
  
  const StateBadge = ({ state, active }: { state: string, active: boolean }) => (
    <div className={`px-3 py-1 rounded-full text-xs font-bold transition-all ${active ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/50' : 'bg-slate-800 text-slate-500 border border-slate-700'}`}>
      {state}
    </div>
  );

  const handleConfigChange = async (key: keyof SimulationConfig, value: string | boolean) => {
    if (typeof value === 'boolean') {
      setConfig({ ...config, [key]: value });
    } else {
      const num = parseFloat(value);
      if (!isNaN(num)) {
        const newConfig = { ...config, [key]: num };
        setConfig(newConfig);
        
        // Auto-sync fan speed changes to Pi in real-time when fan is running
        if (key === 'fanSpeed' && isOnline && fanRunning) {
          try {
            await fetch(`http://${piIp}:8080/update_config`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ fanSpeed: num }),
            });
          } catch (e) {
            console.error("Failed to update fan speed:", e);
          }
        }
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
          <div className="flex items-center gap-2">
            <button
              onClick={onDeployServer}
              disabled={!isOnline}
              className="flex items-center gap-1.5 px-2 py-1 bg-purple-600 hover:bg-purple-500 rounded text-[10px] font-bold text-white uppercase tracking-wide transition-all disabled:opacity-40 disabled:bg-slate-700 disabled:cursor-not-allowed"
              title="Deploy server_py2.py to Pi"
            >
              <Rocket size={12} />
              Deploy Server
            </button>
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
          </div>
          {isOnline && <span className="text-[10px] text-green-500 font-bold animate-pulse">● HEARTBEAT OK</span>}
        </div>
      </div>

      {/* Hardware Power Toggle */}
      <div className="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 rounded-lg">
        <div className="flex items-center gap-2">
          <Zap size={16} className={hardwarePowered ? "text-green-400" : "text-yellow-400"} />
          <div>
            <div className="text-sm font-medium text-slate-200">Hardware Powered</div>
            <div className="text-[10px] text-slate-500">Toggle when 24V PSU is connected</div>
          </div>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={hardwarePowered}
            onChange={(e) => setHardwarePowered(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-green-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
        </label>
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
          className={`p-3 ${fanRunning ? 'bg-blue-600 hover:bg-blue-500' : 'bg-slate-800 hover:bg-slate-700'} disabled:opacity-50 disabled:cursor-not-allowed rounded text-white text-sm flex items-center justify-center gap-2 border ${fanRunning ? 'border-blue-500' : 'border-slate-700'} transition-all active:scale-95`}
        >
          <Wind size={16} /> {fanRunning ? 'Stop Fan' : 'Blow'}
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

      {/* Motor Trimming Section */}
      <div className="mt-6 border-t border-slate-800 pt-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <Settings size={14} /> Motor Trimming
          </h3>
          <div className="flex gap-1 flex-wrap">
            <button
              onClick={saveHome}
              disabled={!isOnline}
              className="flex items-center gap-1 px-2 py-1 bg-green-600 hover:bg-green-500 rounded text-[10px] font-bold text-white uppercase tracking-wide transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              title="Save current position as HOME (OPEN)"
            >
              <Save size={10} />
              Home
            </button>
            <button
              onClick={saveDip}
              disabled={!isOnline}
              className="flex items-center gap-1 px-2 py-1 bg-green-600 hover:bg-green-500 rounded text-[10px] font-bold text-white uppercase tracking-wide transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              title="Save current position as DIP"
            >
              <Save size={10} />
              DIP
            </button>
            <button
              onClick={saveClose}
              disabled={!isOnline}
              className="flex items-center gap-1 px-2 py-1 bg-green-600 hover:bg-green-500 rounded text-[10px] font-bold text-white uppercase tracking-wide transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              title="Save current position as CLOSE"
            >
              <Save size={10} />
              CLOSE
            </button>
            <button
              onClick={returnToHome}
              disabled={!isOnline || isTrimming}
              className="flex items-center gap-1 px-2 py-1 bg-blue-600 hover:bg-blue-500 rounded text-[10px] font-bold text-white uppercase tracking-wide transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              title="Return to HOME position (OPEN arms)"
            >
              <Home size={10} />
              Home
            </button>
          </div>
        </div>
        
        <div className="space-y-3">
          {/* Motor A */}
          <div className="p-3 bg-slate-950 border border-slate-800 rounded">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-slate-300">Motor A</span>
              <span className="text-xs text-slate-500 font-mono">Position: {motorPositions.motorA}</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => trimMotor('A', 'backward', 10)}
                disabled={!isOnline || isTrimming || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all"
              >
                <ArrowLeft size={14} /> 10
              </button>
              <button
                onClick={() => trimMotor('A', 'backward', 1)}
                disabled={!isOnline || isTrimming || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all"
              >
                <ArrowLeft size={14} /> 1
              </button>
              <button
                onClick={() => trimMotor('A', 'forward', 1)}
                disabled={!isOnline || isTrimming || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all"
              >
                1 <ArrowRight size={14} />
              </button>
              <button
                onClick={() => trimMotor('A', 'forward', 10)}
                disabled={!isOnline || isTrimming || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all"
              >
                10 <ArrowRight size={14} />
              </button>
            </div>
          </div>
          
          {/* Motor B */}
          <div className="p-3 bg-slate-950 border border-slate-800 rounded">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-slate-300">Motor B</span>
              <span className="text-xs text-slate-500 font-mono">Position: {motorPositions.motorB}</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => trimMotor('B', 'backward', 10)}
                disabled={!isOnline || isTrimming || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all"
              >
                <ArrowLeft size={14} /> 10
              </button>
              <button
                onClick={() => trimMotor('B', 'backward', 1)}
                disabled={!isOnline || isTrimming || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all"
              >
                <ArrowLeft size={14} /> 1
              </button>
              <button
                onClick={() => trimMotor('B', 'forward', 1)}
                disabled={!isOnline || isTrimming || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all"
              >
                1 <ArrowRight size={14} />
              </button>
              <button
                onClick={() => trimMotor('B', 'forward', 10)}
                disabled={!isOnline || isTrimming || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all"
              >
                10 <ArrowRight size={14} />
              </button>
            </div>
          </div>
          
          <div className="text-[10px] text-slate-500 text-center pt-2 border-t border-slate-800">
            Use trim buttons to fine-tune positions, then click <strong className="text-slate-400">Save Home/DIP/CLOSE</strong> to save. 
            Saved positions will be used automatically in sequences.
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
