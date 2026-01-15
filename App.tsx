
import React, { useState, useEffect, useRef } from 'react';
import Schematic from './components/Schematic';
import ControlPanel from './components/ControlPanel';
import { MachineState, DEFAULT_PINS, SimulationConfig, DEFAULT_CONFIG } from './types';
import { Globe, Zap } from 'lucide-react';

const App: React.FC = () => {
  const [machineState, setMachineState] = useState<MachineState>(MachineState.IDLE);
  const [isRunning, setIsRunning] = useState(false);
  const [piIp, setPiIp] = useState<string>('192.168.0.99'); 
  const [config, setConfig] = useState<SimulationConfig>(DEFAULT_CONFIG);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isPiOnline, setIsPiOnline] = useState(false);
  const [smokeRunning, setSmokeRunning] = useState(false);
  const [fanRunning, setFanRunning] = useState(false);
  const [motorAPosition, setMotorAPosition] = useState<number>(0);
  const [motorBPosition, setMotorBPosition] = useState<number>(0);
  const [movementDuration, setMovementDuration] = useState<number>(0);
  
  const timeoutRef = useRef<any>(null);

  // Heartbeat check for Pi
  useEffect(() => {
    if (!piIp) {
      setIsPiOnline(false);
      return;
    }
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://${piIp}:8080/health`, { signal: AbortSignal.timeout(2000) });
        if (res.ok) {
          const data = await res.json();
          setIsPiOnline(true);
          setMotorAPosition(data.motor_a_position || 0);
          setMotorBPosition(data.motor_b_position || 0);
          setFanRunning(data.fan_running || false);
        } else {
          setIsPiOnline(false);
        }
      } catch {
        setIsPiOnline(false);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [piIp]);

  const stopSimulation = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsRunning(false);
    setMachineState(MachineState.IDLE);
    
    if (piIp && isPiOnline) {
      sendRemoteCommand(MachineState.IDLE);
    }
  };

  const sendRemoteCommand = async (state: MachineState) => {
    if (!piIp) return;
    try {
      const response = await fetch(`http://${piIp}:8080/set_state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state }),
      });
      const data = await response.json();
      // Update motor positions immediately if returned
      if (data.success && data.motor_a_position !== undefined && data.motor_b_position !== undefined) {
        setMotorAPosition(data.motor_a_position);
        setMotorBPosition(data.motor_b_position);
        // Update movement duration for 1:1 simulation
        if (data.movement_duration !== undefined) {
          setMovementDuration(data.movement_duration);
        }
        // Update fan running state
        if (data.fan_running !== undefined) {
          setFanRunning(data.fan_running);
        }
      }
    } catch (e) {
      console.error("Failed to send command to Pi:", e);
    }
  };

  const handleSyncConfig = async () => {
    if (!piIp) return;
    setIsSyncing(true);
    try {
        const response = await fetch(`http://${piIp}:8080/update_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });
        const data = await response.json();
        // Update fan running state if returned
        if (data.fan_running !== undefined) {
          setFanRunning(data.fan_running);
        }
    } catch (e) {
        console.error("Failed to sync config to Pi:", e);
    } finally {
        setIsSyncing(false);
    }
  };

  const handleSmokeControl = async (action: 'start' | 'stop' | 'test') => {
    if (!piIp || !isPiOnline) return;
    try {
      const response = await fetch(`http://${piIp}:8080/control_smoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          intensity: config.smokeIntensity,
          duration: config.smokeDuration,
        }),
      });
      const data = await response.json();
      setSmokeRunning(data.smoke_running || false);
    } catch (e) {
      console.error("Failed to control smoke:", e);
    }
  };

  const handleMotorStep = async (direction: 'up' | 'down' | 'left' | 'right' | 'both_forward' | 'both_backward' | 'motor_a_forward' | 'motor_a_backward' | 'motor_b_forward' | 'motor_b_backward', steps: number = 10) => {
    if (!piIp || !isPiOnline) return;
    try {
      const response = await fetch(`http://${piIp}:8080/motor_step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction, steps }),
      });
      const data = await response.json();
      if (data.success && data.motor_a_position !== undefined && data.motor_b_position !== undefined) {
        // Update positions immediately
        setMotorAPosition(data.motor_a_position);
        setMotorBPosition(data.motor_b_position);
      }
    } catch (e) {
      console.error("Failed to step motor:", e);
    }
  };

  const handleMotorContinuous = async (action: 'start' | 'stop', direction?: 'up' | 'down') => {
    if (!piIp || !isPiOnline) return;
    try {
      const response = await fetch(`http://${piIp}:8080/motor_continuous`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, direction }),
      });
      const data = await response.json();
      // Update positions when stopping continuous movement
      if (action === 'stop' && data.success && data.motor_a_position !== undefined && data.motor_b_position !== undefined) {
        setMotorAPosition(data.motor_a_position);
        setMotorBPosition(data.motor_b_position);
      }
    } catch (e) {
      console.error("Failed to control continuous motor:", e);
    }
  };

  const handleMotorHome = async () => {
    if (!piIp || !isPiOnline) return;
    try {
      const response = await fetch(`http://${piIp}:8080/motor_home`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await response.json();
      if (data.success) {
        // Update local state immediately
        setMotorAPosition(0);
        setMotorBPosition(0);
      }
    } catch (e) {
      console.error("Failed to calibrate motors:", e);
    }
  };

  const handleSaveMotorPosition = async (state: 'DIP' | 'OPEN' | 'CLOSE') => {
    if (!piIp || !isPiOnline) return;
    try {
      const response = await fetch(`http://${piIp}:8080/save_motor_position`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state }),
      });
      const data = await response.json();
      if (data.success && data.config) {
        // Update config with saved positions
        setConfig({
          ...config,
          motorADipPosition: data.config.motorADipPosition || config.motorADipPosition,
          motorBDipPosition: data.config.motorBDipPosition || config.motorBDipPosition,
          motorAOpenPosition: data.config.motorAOpenPosition || config.motorAOpenPosition,
          motorBOpenPosition: data.config.motorBOpenPosition || config.motorBOpenPosition,
          motorAClosePosition: data.config.motorAClosePosition || config.motorAClosePosition,
          motorBClosePosition: data.config.motorBClosePosition || config.motorBClosePosition,
        });
      }
    } catch (e) {
      console.error("Failed to save motor position:", e);
    }
  };

  const runSequenceStep = (step: MachineState) => {
    setMachineState(step);
    if (piIp && isPiOnline) sendRemoteCommand(step);

    let nextStep: MachineState = MachineState.IDLE;
    let waitDuration = 1000; // Wait time after movement completes

    switch (step) {
      case MachineState.OPEN:
        // After OPEN, wait then go to CLOSE
        nextStep = MachineState.CLOSE;
        waitDuration = config.waitAfterOpen * 1000;
        break;
      case MachineState.CLOSE:
        // After CLOSE, wait then go to DIP
        nextStep = MachineState.DIP;
        waitDuration = config.waitAfterClose * 1000;
        break;
      case MachineState.DIP:
        // After DIP, wait then go to OPEN
        nextStep = MachineState.OPEN;
        waitDuration = config.waitAfterDip * 1000;
        break;
    }

    // Calculate movement duration for the current step to add to wait time
    const movementDuration = calculateMovementDuration(step);
    const totalDuration = (movementDuration * 1000) + waitDuration;

    timeoutRef.current = setTimeout(() => {
        runSequenceStep(nextStep);
    }, totalDuration);
  };

  const toggleRun = () => {
    if (isRunning) {
      stopSimulation();
    } else {
      setIsRunning(true);
      // Start loop with OPEN state
      runSequenceStep(MachineState.OPEN);
    }
  };

  const calculateMovementDuration = (state: MachineState): number => {
    // Calculate duration based on current position and target position
    // Each step takes 0.001s (high) + 0.001s (low) = 0.002s per step
    const stepDelay = 0.002; // seconds per step
    
    let targetA = 0;
    let targetB = 0;
    
    switch (state) {
      case MachineState.DIP:
        targetA = config.motorADipPosition || 200;
        targetB = config.motorBDipPosition || -200;
        break;
      case MachineState.OPEN:
      case MachineState.HOME:
        targetA = 0;
        targetB = 0;
        break;
      case MachineState.CLOSE:
        targetA = config.motorAClosePosition || 200;
        targetB = config.motorBClosePosition || -200;
        break;
      default:
        return 0;
    }
    
    const stepsA = Math.abs(targetA - motorAPosition);
    const stepsB = Math.abs(targetB - motorBPosition);
    const maxSteps = Math.max(stepsA, stepsB);
    
    return maxSteps * stepDelay;
  };

  const handleManualState = (state: MachineState) => {
    stopSimulation();
    
    // Calculate and set duration immediately for 1:1 animation
    const duration = calculateMovementDuration(state);
    setMovementDuration(duration);
    
    // Set state immediately to start animation
    setMachineState(state);
    
    if (piIp && isPiOnline) {
      handleSyncConfig().then(() => sendRemoteCommand(state));
    }
  };

  return (
    <div className="h-screen bg-slate-950 flex flex-col overflow-hidden">
      
      <header className="flex-none p-4 md:px-8 md:py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 bg-slate-950 z-10">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-slate-100 flex items-center gap-3 text-shadow-glow">
            <Zap className="text-purple-500 w-8 h-8" />
            BubbleBot Remote IDE
          </h1>
          <div className="flex items-center gap-2 mt-1">
             <span className="bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest border border-purple-500/20">Phase 4: Remote Deployment</span>
             <p className="text-slate-400 text-sm flex items-center gap-2">
               <Globe size={14} className={isPiOnline ? "text-green-500 animate-pulse" : "text-slate-600"} />
               {isPiOnline ? `Connected to Pi @ ${piIp}` : 'Awaiting Connection to Cursor / Pi'}
             </p>
          </div>
        </div>
      </header>

      <main className="flex-1 min-h-0 p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-y-auto lg:overflow-hidden">
        
        <div className="lg:col-span-8 flex flex-col h-[600px] lg:h-full min-h-0 bg-slate-900 rounded-xl border border-slate-800 shadow-2xl overflow-hidden relative">
          <div className="absolute inset-0">
             <Schematic activeState={machineState} fanSpeed={config.fanSpeed} fanEnabled={config.fanEnabled} fanRunning={fanRunning} highlight={null} motorAPosition={motorAPosition} motorBPosition={motorBPosition} movementDuration={movementDuration} />
          </div>
        </div>

        <div className="lg:col-span-4 flex flex-col gap-6 h-full min-h-0 overflow-y-auto custom-scrollbar">
           
           <div className="flex-none rounded-xl border border-slate-700 shadow-xl bg-slate-900">
              <ControlPanel 
                currentState={machineState}
                isRunning={isRunning}
                onToggleRun={toggleRun}
                onManualState={handleManualState}
                pins={DEFAULT_PINS}
                piIp={piIp}
                setPiIp={setPiIp}
                config={config}
                setConfig={setConfig}
                onSyncConfig={handleSyncConfig}
                isSyncing={isSyncing}
                isOnline={isPiOnline}
                smokeRunning={smokeRunning}
                onSmokeControl={handleSmokeControl}
                onMotorStep={handleMotorStep}
                onMotorContinuous={handleMotorContinuous}
                onMotorHome={handleMotorHome}
                onSaveMotorPosition={handleSaveMotorPosition}
                motorAPosition={motorAPosition}
                motorBPosition={motorBPosition}
                fanRunning={fanRunning}
              />
           </div>

        </div>

      </main>
    </div>
  );
};

export default App;
