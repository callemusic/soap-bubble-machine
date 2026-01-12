
import React, { useState, useEffect, useRef } from 'react';
import { MachineState, PinConfig, SimulationConfig } from '../types';
import { Play, Square, RefreshCw, Wind, ArrowDownToLine, MoveVertical, ExternalLink, CloudFog, Wifi, Settings, Fan, UploadCloud, Activity, Zap, Rocket, ArrowLeft, ArrowRight, Home, Save, RotateCcw, FolderOpen, Trash2, FolderPlus } from 'lucide-react';

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
  setups: Record<string, any>;
  setupName: string;
  setSetupName: (name: string) => void;
  onSaveSetup: () => void;
  onLoadSetup: (name: string) => void;
  onDeleteSetup: (name: string) => void;
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
  motorAEnabled?: boolean;
  motorBEnabled?: boolean;
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
  onDeployServer,
  setups,
  setupName,
  setSetupName,
  onSaveSetup,
  onLoadSetup,
  onDeleteSetup
}) => {
  const [motorPositions, setMotorPositions] = useState<MotorPositions>({ 
    motorA: 0, 
    motorB: 0, 
    homeA: 0, 
    homeB: 0,
    motorAEnabled: true,
    motorBEnabled: true
  });
  const [isTrimming, setIsTrimming] = useState(false);
  const continuousTrimIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const continuousTrimParamsRef = useRef<{motor: 'A' | 'B', direction: 'forward' | 'backward', steps: number} | null>(null);
  
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
  
  const trimMotor = async (motor: 'A' | 'B', direction: 'forward' | 'backward', steps: number = 10, allowContinuous: boolean = false) => {
    if (!isOnline) return;
    // Only check isTrimming if not allowing continuous calls
    if (!allowContinuous && isTrimming) return;
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
      // Only clear isTrimming if not in continuous mode
      if (!allowContinuous) {
        setIsTrimming(false);
      }
    }
  };

  const startContinuousTrim = (motor: 'A' | 'B', direction: 'forward' | 'backward', steps: number) => {
    if (!isOnline || isRunning || continuousTrimIntervalRef.current) return;
    
    // Stop any existing continuous trim
    stopContinuousTrim();
    
    // Store params for the interval
    continuousTrimParamsRef.current = { motor, direction, steps };
    
    // Start with immediate trim
    trimMotor(motor, direction, steps, true);
    
    // Then continue trimming at regular intervals (every 100ms for smooth continuous movement)
    continuousTrimIntervalRef.current = setInterval(() => {
      if (continuousTrimParamsRef.current) {
        trimMotor(
          continuousTrimParamsRef.current.motor,
          continuousTrimParamsRef.current.direction,
          continuousTrimParamsRef.current.steps,
          true
        );
      }
    }, 100); // 100ms interval = 10 trims per second
  };

  const stopContinuousTrim = () => {
    if (continuousTrimIntervalRef.current) {
      clearInterval(continuousTrimIntervalRef.current);
      continuousTrimIntervalRef.current = null;
    }
    continuousTrimParamsRef.current = null;
    setIsTrimming(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopContinuousTrim();
    };
  }, []);
  
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
  
  const resetMotorPositions = async () => {
    if (!isOnline) return;
    if (!confirm('Reset motor positions to 0,0?\n\n⚠️ IMPORTANT: Physically align motors to 0,0 position FIRST, then click OK.\n\nThis sets the software position to match the physical position.')) {
      return;
    }
    try {
      const res = await fetch(`http://${piIp}:8080/reset_motor_positions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.positions) {
          setMotorPositions(data.positions);
        }
        alert('✅ Motor positions reset to 0,0\n\nMotors should now be physically aligned to this position.');
      }
    } catch (e) {
      console.error("Failed to reset positions:", e);
      alert('❌ Failed to reset motor positions');
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
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">DIP Wait (s)</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={config.dipWait}
                  onChange={(e) => handleConfigChange('dipWait', e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Seconds arms stay at DIP position after reaching it"
                />
             </div>
             <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">OPEN Wait (s)</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={config.openWait}
                  onChange={(e) => handleConfigChange('openWait', e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Seconds arms stay at OPEN position after reaching it"
                />
             </div>
             <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">CLOSE Wait (s)</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={config.closeWait}
                  onChange={(e) => handleConfigChange('closeWait', e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Seconds arms stay at CLOSE position after reaching it"
                />
             </div>
             <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Fan Start Delay</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={config.fanStartDelay}
                  onChange={(e) => handleConfigChange('fanStartDelay', e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Seconds delay after DIP phase ends before fan starts"
                />
             </div>
             <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Fan Duration</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={config.fanDuration}
                  onChange={(e) => handleConfigChange('fanDuration', e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Total seconds fan should run (independent of arm movement - fan continues during CLOSE)"
                />
             </div>
          </div>
        </div>
      </div>

      {/* Movement Speed Controls */}
      <div className="mt-6 border-t border-slate-800 pt-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <Settings size={14} /> Movement Speed
          </h3>
        </div>
        
        <div className="space-y-4">
          {/* DIP to OPEN */}
          <div className="p-3 bg-slate-950 border border-slate-800 rounded">
            <h4 className="text-xs font-semibold text-slate-400 mb-3">DIP → OPEN</h4>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Speed (s)</label>
                <input 
                  type="number" 
                  step="0.0001"
                  value={config.dipToOpenSpeed}
                  onChange={(e) => handleConfigChange('dipToOpenSpeed', parseFloat(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Base step delay in seconds (lower = faster)"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Ramp-Up (steps)</label>
                <input 
                  type="number" 
                  step="1"
                  value={config.dipToOpenRampUp}
                  onChange={(e) => handleConfigChange('dipToOpenRampUp', parseInt(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Number of steps at start to accelerate (0 = no ramp-up)"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Slow-In (steps)</label>
                <input 
                  type="number" 
                  step="1"
                  value={config.dipToOpenSlowIn}
                  onChange={(e) => handleConfigChange('dipToOpenSlowIn', parseInt(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Number of steps before target to start deceleration (0 = no slow-in)"
                />
              </div>
            </div>
          </div>

          {/* OPEN to CLOSE */}
          <div className="p-3 bg-slate-950 border border-slate-800 rounded">
            <h4 className="text-xs font-semibold text-slate-400 mb-3">OPEN → CLOSE</h4>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Speed (s)</label>
                <input 
                  type="number" 
                  step="0.0001"
                  value={config.openToCloseSpeed}
                  onChange={(e) => handleConfigChange('openToCloseSpeed', parseFloat(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Base step delay in seconds (lower = faster)"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Ramp-Up (steps)</label>
                <input 
                  type="number" 
                  step="1"
                  value={config.openToCloseRampUp}
                  onChange={(e) => handleConfigChange('openToCloseRampUp', parseInt(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Number of steps at start to accelerate (0 = no ramp-up)"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Slow-In (steps)</label>
                <input 
                  type="number" 
                  step="1"
                  value={config.openToCloseSlowIn}
                  onChange={(e) => handleConfigChange('openToCloseSlowIn', parseInt(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Number of steps before target to start deceleration (0 = no slow-in)"
                />
              </div>
            </div>
          </div>

          {/* CLOSE to DIP */}
          <div className="p-3 bg-slate-950 border border-slate-800 rounded">
            <h4 className="text-xs font-semibold text-slate-400 mb-3">CLOSE → DIP</h4>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Speed (s)</label>
                <input 
                  type="number" 
                  step="0.0001"
                  value={config.closeToDipSpeed}
                  onChange={(e) => handleConfigChange('closeToDipSpeed', parseFloat(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Base step delay in seconds (lower = faster)"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Ramp-Up (steps)</label>
                <input 
                  type="number" 
                  step="1"
                  value={config.closeToDipRampUp}
                  onChange={(e) => handleConfigChange('closeToDipRampUp', parseInt(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Number of steps at start to accelerate (0 = no ramp-up)"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-tighter">Slow-In (steps)</label>
                <input 
                  type="number" 
                  step="1"
                  value={config.closeToDipSlowIn}
                  onChange={(e) => handleConfigChange('closeToDipSlowIn', parseInt(e.target.value))}
                  className="bg-slate-900 border border-slate-700 rounded w-full py-1 px-2 text-sm text-slate-300 outline-none focus:border-blue-500"
                  title="Number of steps before target to start deceleration (0 = no slow-in)"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Motor Position Status */}
      <div className="mt-6 border-t border-slate-800 pt-4">
        <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-yellow-400 uppercase tracking-wide">Current Motor Positions</span>
            <button
              onClick={resetMotorPositions}
              disabled={!isOnline || isRunning}
              className="flex items-center gap-1 px-2 py-1 bg-yellow-600 hover:bg-yellow-500 rounded text-[10px] font-bold text-white uppercase tracking-wide transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              title="Reset positions to 0,0 - align motors physically first!"
            >
              <RotateCcw size={10} />
              Reset to 0,0
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Motor A:</span>
              <div className="flex items-center gap-2">
                <span className="text-yellow-300 font-mono font-bold">{motorPositions.motorA}</span>
                <button
                  onClick={async () => {
                    const newState = !(motorPositions.motorAEnabled ?? true);
                    try {
                      const res = await fetch(`http://${piIp}:8080/set_motor_enabled`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ motor: 'A', enabled: newState }),
                      });
                      if (res.ok) {
                        const data = await res.json();
                        if (data.positions) {
                          setMotorPositions(data.positions);
                        }
                      }
                    } catch (e) {
                      console.error("Failed to toggle motor:", e);
                    }
                  }}
                  disabled={!isOnline}
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase transition-all disabled:opacity-40 ${
                    motorPositions.motorAEnabled !== false 
                      ? 'bg-green-600 hover:bg-green-500 text-white' 
                      : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  }`}
                  title={motorPositions.motorAEnabled !== false ? "Disable Motor A" : "Enable Motor A"}
                >
                  {motorPositions.motorAEnabled !== false ? 'ON' : 'OFF'}
                </button>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Motor B:</span>
              <div className="flex items-center gap-2">
                <span className="text-yellow-300 font-mono font-bold">{motorPositions.motorB}</span>
                <button
                  onClick={async () => {
                    const newState = !(motorPositions.motorBEnabled ?? true);
                    try {
                      const res = await fetch(`http://${piIp}:8080/set_motor_enabled`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ motor: 'B', enabled: newState }),
                      });
                      if (res.ok) {
                        const data = await res.json();
                        if (data.positions) {
                          setMotorPositions(data.positions);
                        }
                      }
                    } catch (e) {
                      console.error("Failed to toggle motor:", e);
                    }
                  }}
                  disabled={!isOnline}
                  className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase transition-all disabled:opacity-40 ${
                    motorPositions.motorBEnabled !== false 
                      ? 'bg-green-600 hover:bg-green-500 text-white' 
                      : 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  }`}
                  title={motorPositions.motorBEnabled !== false ? "Disable Motor B" : "Enable Motor B"}
                >
                  {motorPositions.motorBEnabled !== false ? 'ON' : 'OFF'}
                </button>
              </div>
            </div>
          </div>
          <div className="text-[10px] text-slate-500">
            Disabled motors won't move during sequences. Enable state is saved with setups.
          </div>
          <div className="text-[10px] text-yellow-400/70 mt-2">
            ⚠️ Always reset to 0,0 after server restart or code update, then physically align motors
          </div>
        </div>
      </div>

      {/* Motor Setups/Scenes */}
      <div className="mt-6 border-t border-slate-800 pt-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <FolderOpen size={14} /> Motor Setups / Scenes
          </h3>
        </div>
        
        <div className="space-y-3">
          {/* Save Setup */}
          <div className="flex gap-2">
            <input
              type="text"
              value={setupName}
              onChange={(e) => setSetupName(e.target.value)}
              placeholder="Setup name..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-300 outline-none focus:border-blue-500"
              onKeyPress={(e) => {
                if (e.key === 'Enter' && setupName.trim()) {
                  onSaveSetup();
                }
              }}
            />
            <button
              onClick={onSaveSetup}
              disabled={!isOnline || !setupName.trim()}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs font-semibold text-white uppercase tracking-wide transition-all disabled:opacity-40 disabled:bg-slate-700 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <FolderPlus size={12} /> Save
            </button>
          </div>

          {/* List of Setups */}
          {Object.keys(setups).length > 0 && (
            <div className="space-y-2">
              {Object.keys(setups).map((name) => (
                <div key={name} className="flex items-center gap-2 p-2 bg-slate-950 border border-slate-800 rounded">
                  <span className="flex-1 text-xs text-slate-300">{name}</span>
                  <button
                    onClick={() => onLoadSetup(name)}
                    disabled={!isOnline}
                    className="px-2 py-1 bg-green-600 hover:bg-green-500 rounded text-[10px] font-semibold text-white uppercase transition-all disabled:opacity-40 disabled:bg-slate-700 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    <FolderOpen size={10} /> Load
                  </button>
                  <button
                    onClick={() => onDeleteSetup(name)}
                    disabled={!isOnline}
                    className="px-2 py-1 bg-red-600 hover:bg-red-500 rounded text-[10px] font-semibold text-white uppercase transition-all disabled:opacity-40 disabled:bg-slate-700 disabled:cursor-not-allowed flex items-center gap-1"
                  >
                    <Trash2 size={10} />
                  </button>
                </div>
              ))}
            </div>
          )}
          
          {Object.keys(setups).length === 0 && (
            <div className="text-xs text-slate-500 text-center py-2">
              No saved setups. Save current motor positions as a setup above.
            </div>
          )}
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
                onMouseDown={() => startContinuousTrim('A', 'backward', 10)}
                onMouseUp={stopContinuousTrim}
                onMouseLeave={stopContinuousTrim}
                onTouchStart={() => startContinuousTrim('A', 'backward', 10)}
                onTouchEnd={stopContinuousTrim}
                disabled={!isOnline || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all select-none"
              >
                <ArrowLeft size={14} /> 10
              </button>
              <button
                onClick={() => trimMotor('A', 'backward', 1)}
                onMouseDown={() => startContinuousTrim('A', 'backward', 1)}
                onMouseUp={stopContinuousTrim}
                onMouseLeave={stopContinuousTrim}
                onTouchStart={() => startContinuousTrim('A', 'backward', 1)}
                onTouchEnd={stopContinuousTrim}
                disabled={!isOnline || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all select-none"
              >
                <ArrowLeft size={14} /> 1
              </button>
              <button
                onClick={() => trimMotor('A', 'forward', 1)}
                onMouseDown={() => startContinuousTrim('A', 'forward', 1)}
                onMouseUp={stopContinuousTrim}
                onMouseLeave={stopContinuousTrim}
                onTouchStart={() => startContinuousTrim('A', 'forward', 1)}
                onTouchEnd={stopContinuousTrim}
                disabled={!isOnline || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all select-none"
              >
                1 <ArrowRight size={14} />
              </button>
              <button
                onClick={() => trimMotor('A', 'forward', 10)}
                onMouseDown={() => startContinuousTrim('A', 'forward', 10)}
                onMouseUp={stopContinuousTrim}
                onMouseLeave={stopContinuousTrim}
                onTouchStart={() => startContinuousTrim('A', 'forward', 10)}
                onTouchEnd={stopContinuousTrim}
                disabled={!isOnline || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all select-none"
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
                onMouseDown={() => startContinuousTrim('B', 'backward', 10)}
                onMouseUp={stopContinuousTrim}
                onMouseLeave={stopContinuousTrim}
                onTouchStart={() => startContinuousTrim('B', 'backward', 10)}
                onTouchEnd={stopContinuousTrim}
                disabled={!isOnline || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all select-none"
              >
                <ArrowLeft size={14} /> 10
              </button>
              <button
                onClick={() => trimMotor('B', 'backward', 1)}
                onMouseDown={() => startContinuousTrim('B', 'backward', 1)}
                onMouseUp={stopContinuousTrim}
                onMouseLeave={stopContinuousTrim}
                onTouchStart={() => startContinuousTrim('B', 'backward', 1)}
                onTouchEnd={stopContinuousTrim}
                disabled={!isOnline || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all select-none"
              >
                <ArrowLeft size={14} /> 1
              </button>
              <button
                onClick={() => trimMotor('B', 'forward', 1)}
                onMouseDown={() => startContinuousTrim('B', 'forward', 1)}
                onMouseUp={stopContinuousTrim}
                onMouseLeave={stopContinuousTrim}
                onTouchStart={() => startContinuousTrim('B', 'forward', 1)}
                onTouchEnd={stopContinuousTrim}
                disabled={!isOnline || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all select-none"
              >
                1 <ArrowRight size={14} />
              </button>
              <button
                onClick={() => trimMotor('B', 'forward', 10)}
                onMouseDown={() => startContinuousTrim('B', 'forward', 10)}
                onMouseUp={stopContinuousTrim}
                onMouseLeave={stopContinuousTrim}
                onTouchStart={() => startContinuousTrim('B', 'forward', 10)}
                onTouchEnd={stopContinuousTrim}
                disabled={!isOnline || isRunning}
                className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-xs text-slate-200 transition-all select-none"
              >
                10 <ArrowRight size={14} />
              </button>
            </div>
          </div>
          
          <div className="text-[10px] text-slate-500 text-center pt-2 border-t border-slate-800">
            Click trim buttons for single moves, or <strong className="text-slate-400">hold down</strong> for continuous trimming. 
            Then click <strong className="text-slate-400">Save Home/DIP/CLOSE</strong> to save. 
            Saved positions will be used automatically in sequences.
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
