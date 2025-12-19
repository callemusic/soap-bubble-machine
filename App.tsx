
import React, { useState, useEffect, useRef } from 'react';
import Schematic from './components/Schematic';
import ControlPanel from './components/ControlPanel';
import CodeGenerator from './components/CodeGenerator';
import PinoutGuide from './components/PinoutGuide';
import WiringAssistant from './components/WiringAssistant';
import { MachineState, DEFAULT_PINS, SimulationConfig, DEFAULT_CONFIG, SystemHighlight } from './types';
import { CircuitBoard, Globe, Zap } from 'lucide-react';

const App: React.FC = () => {
  const [machineState, setMachineState] = useState<MachineState>(MachineState.IDLE);
  const [isRunning, setIsRunning] = useState(false);
  const [piIp, setPiIp] = useState<string>('192.168.2.108'); 
  const [config, setConfig] = useState<SimulationConfig>(DEFAULT_CONFIG);
  const [isSyncing, setIsSyncing] = useState(false);
  const [highlight, setHighlight] = useState<SystemHighlight>(null);
  const [isPiOnline, setIsPiOnline] = useState(false);
  const [hardwarePowered, setHardwarePowered] = useState<boolean>(false); // Manual toggle - user sets when power is confirmed
  const [fanRunning, setFanRunning] = useState<boolean>(false);
  
  const timeoutRef = useRef<any>(null);

  // Heartbeat check for Pi and fan status, sync state
  useEffect(() => {
    if (!piIp) {
      setIsPiOnline(false);
      setFanRunning(false);
      return;
    }
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://${piIp}:8080/health`, { signal: AbortSignal.timeout(2000) });
        setIsPiOnline(res.ok);
        if (res.ok) {
          const data = await res.json();
          setFanRunning(data.fan_running || false);
          // Sync machine state if available and not running auto sequence
          if (data.current_position && !isRunning && data.current_position !== 'IDLE') {
            // Only sync if it's a valid state
            const validStates = ['DIP', 'OPEN', 'CLOSE', 'IDLE'];
            if (validStates.includes(data.current_position)) {
              setMachineState(data.current_position as MachineState);
            }
          }
        } else {
          setFanRunning(false);
        }
      } catch {
        setIsPiOnline(false);
        setFanRunning(false);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [piIp, isRunning]);

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
    if (!piIp) return null;
    try {
      const res = await fetch(`http://${piIp}:8080/set_state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state }),
      });
      if (res.ok) {
        try {
          const data = await res.json();
          // Update fan state if BLOW was toggled
          if (state === MachineState.BLOW && data.fan_running !== undefined) {
            setFanRunning(data.fan_running);
          }
          // Sync current position from server if provided
          if (data.current_position && !isRunning) {
            const validStates = ['DIP', 'OPEN', 'CLOSE', 'IDLE'];
            if (validStates.includes(data.current_position)) {
              setMachineState(data.current_position as MachineState);
            }
          }
        } catch {}
      }
      return res;
    } catch (e) {
      console.error("Failed to send command to Pi:", e);
      return null;
    }
  };

  const handleSyncConfig = async () => {
    if (!piIp) return;
    setIsSyncing(true);
    try {
        await fetch(`http://${piIp}:8080/update_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });
    } catch (e) {
        console.error("Failed to sync config to Pi:", e);
    } finally {
        setIsSyncing(false);
    }
  };

  const runSequenceStep = (step: MachineState) => {
    setMachineState(step);
    if (piIp && isPiOnline) sendRemoteCommand(step);

    let nextStep: MachineState = MachineState.IDLE;
    let duration = 1000;

    switch (step) {
      case MachineState.DIP:
        nextStep = MachineState.OPEN;
        duration = config.dipDuration * 1000; 
        break;
      case MachineState.OPEN:
        nextStep = MachineState.BLOW;
        duration = config.liftDuration * 1000; 
        break;
      case MachineState.BLOW:
        nextStep = MachineState.CLOSE;
        duration = config.blowDuration * 1000;
        break;
      case MachineState.CLOSE:
        nextStep = MachineState.DIP; 
        duration = config.closeDuration * 1000;
        break;
    }

    timeoutRef.current = setTimeout(() => {
        runSequenceStep(nextStep);
    }, duration);
  };

  const toggleRun = () => {
    if (isRunning) {
      stopSimulation();
    } else {
      setIsRunning(true);
      runSequenceStep(MachineState.DIP);
    }
  };

  const handleManualState = async (state: MachineState) => {
    // Skip if already in this state (except BLOW which toggles)
    if (state !== MachineState.BLOW && state === machineState) {
      console.log(`Already in ${state} state - skipping`);
      return;
    }
    
    // For BLOW, don't stop simulation first - just toggle the fan
    // For other states, stop the simulation first
    if (state !== MachineState.BLOW) {
      stopSimulation();
    } else {
      // Just stop the auto-sequence timer, but don't send IDLE
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      setIsRunning(false);
    }
    setMachineState(state);
    if (piIp && isPiOnline) {
      await handleSyncConfig();
      await sendRemoteCommand(state);
    }
  };

  const handleDeployServer = async () => {
    if (!piIp || !isPiOnline) {
      alert('Pi must be online to deploy server');
      return;
    }

    // Create file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.py';
    input.onchange = async (e: any) => {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = async (event: any) => {
        const code = event.target.result;
        try {
          const res = await fetch(`http://${piIp}:8080/upload_server`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
          });
          const data = await res.json();
          if (data.success) {
            alert('✅ Server code deployed! The server will need to be restarted manually on the Pi.');
          } else {
            alert(`❌ Deployment failed: ${data.error || 'Unknown error'}`);
          }
        } catch (error) {
          alert(`❌ Failed to deploy: ${error}`);
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  return (
    <div className="h-screen bg-slate-950 flex flex-col overflow-hidden">
      
      <header className="flex-none p-4 md:px-8 md:py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 bg-slate-950 z-10">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-slate-100 flex items-center gap-3 text-shadow-glow">
            <Zap className="text-purple-500 w-8 h-8" />
            BubbleBot Remote IDE
          </h1>
          <div className="flex flex-col gap-2 mt-1">
             <div className="flex items-center gap-2">
               <span className="bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest border border-purple-500/20">Phase 4: Remote Deployment</span>
               <p className="text-slate-400 text-sm flex items-center gap-2">
                 <Globe size={14} className={isPiOnline ? "text-green-500 animate-pulse" : "text-slate-600"} />
                 {isPiOnline ? `Connected to Pi @ ${piIp}` : 'Awaiting Connection to Cursor / Pi'}
               </p>
             </div>
             {isPiOnline && !hardwarePowered && (
               <div className="flex items-center gap-2 px-3 py-2 bg-yellow-500/10 border border-yellow-500/30 rounded text-yellow-400 text-xs">
                 <Zap size={14} className="text-yellow-400" />
                 <span className="font-bold">NOTE:</span>
                 <span>Hardware power not confirmed. Toggle "Hardware Powered" below when 24V PSU is connected.</span>
               </div>
             )}
          </div>
        </div>
      </header>

      <main className="flex-1 min-h-0 p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-y-auto lg:overflow-hidden">
        
        <div className="lg:col-span-8 flex flex-col h-[600px] lg:h-full min-h-0 bg-slate-900 rounded-xl border border-slate-800 shadow-2xl overflow-hidden relative">
          <div className="absolute inset-0">
             <Schematic activeState={machineState} fanSpeed={config.fanSpeed} fanEnabled={config.fanEnabled} highlight={highlight} />
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
                hardwarePowered={hardwarePowered}
                setHardwarePowered={setHardwarePowered}
                fanRunning={fanRunning}
                onDeployServer={handleDeployServer}
              />
           </div>

           <div className="flex-none min-h-[300px]">
              <WiringAssistant onHighlight={setHighlight} />
           </div>

           <div className="flex-none min-h-[450px]">
              <PinoutGuide pins={DEFAULT_PINS} onHighlight={setHighlight} />
           </div>

           <div className="flex-1 min-h-[400px]">
              <CodeGenerator pins={DEFAULT_PINS} config={config} piIp={piIp} />
           </div>

        </div>

      </main>
    </div>
  );
};

export default App;
