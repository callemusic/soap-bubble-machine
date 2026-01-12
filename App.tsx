
import React, { useState, useEffect, useRef } from 'react';
import Schematic from './components/Schematic';
import ControlPanel from './components/ControlPanel';
import CodeGenerator from './components/CodeGenerator';
import PinoutGuide from './components/PinoutGuide';
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
  const isRunningRef = useRef<boolean>(false);
  const configRef = useRef<SimulationConfig>(config);
  
  // Keep config ref in sync with state (so sequence always uses latest values)
  useEffect(() => {
    configRef.current = config;
    console.log('Config updated in ref:', config);
  }, [config]);

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

  const stopSimulation = async () => {
    // Set running flag to false immediately to stop sequence
    isRunningRef.current = false;
    setIsRunning(false);
    
    // Clear any pending timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    
    // Move arms back to HOME/OPEN before stopping
    if (piIp && isPiOnline) {
      try {
        // First return to home (movement is blocking on server, so response comes after movement completes)
        const res = await fetch(`http://${piIp}:8080/return_home`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        if (res.ok) {
          // Movement is complete, now stop everything
          await sendRemoteCommand(MachineState.IDLE);
        }
      } catch (e) {
        console.error("Failed to return home:", e);
        // Still send IDLE even if return home failed
        sendRemoteCommand(MachineState.IDLE);
      }
    }
    
    setMachineState(MachineState.IDLE);
  };

  const sendRemoteCommand = async (state: MachineState, isSequence: boolean = false) => {
    if (!piIp) return null;
    try {
      const res = await fetch(`http://${piIp}:8080/set_state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state, isSequence }),
      });
      if (res.ok) {
        try {
          const data = await res.json();
          // Update fan state if BLOW was toggled
          if (state === MachineState.BLOW && data.fan_running !== undefined) {
            setFanRunning(data.fan_running);
            console.log(`Fan toggled via BLOW: ${data.fan_running ? 'ON' : 'OFF'}`);
          }
          // Sync current position from server if provided
          if (data.current_position && !isRunning) {
            const validStates = ['DIP', 'OPEN', 'CLOSE', 'IDLE'];
            if (validStates.includes(data.current_position)) {
              setMachineState(data.current_position as MachineState);
            }
          }
          // For movements, ensure we wait for the response to be fully processed
          // The server sends response AFTER movement completes (blocking)
          return res;
        } catch (e) {
          console.error("Failed to parse response:", e);
          return res; // Still return res even if JSON parse fails
        }
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
        // Prepare config for Pi - ensure we use correct property names
        const configToSend: any = { ...config };
        // Remove old property names if they exist
        if ('fanEarlyStart' in configToSend) {
            delete configToSend.fanEarlyStart;
        }
        if ('dipDuration' in configToSend) {
            delete configToSend.dipDuration;
        }
        if ('liftDuration' in configToSend) {
            delete configToSend.liftDuration;
        }
        if ('closeDuration' in configToSend) {
            delete configToSend.closeDuration;
        }
        // Ensure new property names exist (migrate from old names if needed)
        if (!('fanStartDelay' in configToSend)) {
            configToSend.fanStartDelay = (config as any).fanEarlyStart || 0.0;
        }
        if (!('dipWait' in configToSend)) {
            configToSend.dipWait = (config as any).dipDuration || 3.0;
        }
        if (!('openWait' in configToSend)) {
            configToSend.openWait = (config as any).liftDuration || 4.0;
        }
        if (!('closeWait' in configToSend)) {
            configToSend.closeWait = (config as any).closeDuration || 1.0;
        }
        
        await fetch(`http://${piIp}:8080/update_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configToSend),
        });
    } catch (e) {
        console.error("Failed to sync config to Pi:", e);
    } finally {
        setIsSyncing(false);
    }
  };

  const runSequenceStep = async (step: MachineState) => {
    // Check if sequence was stopped - don't continue if stopped (use ref for current value)
    if (!isRunningRef.current) {
      console.log(`Sequence stopped, aborting ${step}`);
      return;
    }
    
    setMachineState(step);
    
    // Get current config values from ref (always latest, avoids stale closures)
    const currentConfig = configRef.current;
    
    let nextStep: MachineState = MachineState.IDLE;
    let duration = 1000;

    // For movements (DIP, OPEN, CLOSE), wait for movement to complete before starting wait timer
    if (piIp && isPiOnline && (step === MachineState.DIP || step === MachineState.OPEN || step === MachineState.CLOSE)) {
      // Send command and wait for response (movement completes before response)
      const response = await sendRemoteCommand(step, true); // true = part of sequence
      
      // Check again if sequence was stopped during movement (use ref for current value)
      if (!isRunningRef.current) {
        console.log(`Sequence stopped during ${step} movement, aborting`);
        return;
      }
      
      if (!response || !response.ok) {
        console.error(`Failed to execute ${step}, stopping sequence`);
        isRunningRef.current = false;
        setIsRunning(false);
        return;
      }
      // Movement is now complete, wait timer will start below
      console.log(`${step} movement complete, starting wait timer`);
    } else if (piIp && isPiOnline) {
      sendRemoteCommand(step, true); // true = part of sequence
    }

    // Check again before setting timeout
    if (!isRunningRef.current) {
      console.log(`Sequence stopped before setting timeout for ${step}, aborting`);
      return;
    }

    // Read config values fresh for this step (to ensure we use latest values)
    switch (step) {
      case MachineState.DIP:
        nextStep = MachineState.OPEN;
        duration = currentConfig.dipWait * 1000;  // Wait AFTER movement completes
        console.log(`DIP wait: ${currentConfig.dipWait}s (from config)`);
        break;
      case MachineState.OPEN:
        nextStep = MachineState.CLOSE;  // Skip BLOW, go directly to CLOSE
        duration = currentConfig.openWait * 1000;  // Wait AFTER movement completes
        console.log(`OPEN wait: ${currentConfig.openWait}s (from config)`);
        break;
      case MachineState.CLOSE:
        nextStep = MachineState.DIP; 
        duration = currentConfig.closeWait * 1000;  // Wait AFTER movement completes
        console.log(`CLOSE wait: ${currentConfig.closeWait}s (from config)`);
        break;
      case MachineState.BLOW:
        // BLOW is no longer part of automatic sequence, only manual control
        nextStep = MachineState.IDLE;
        duration = 1000;
        break;
    }

    // Final check before setting timeout
    if (!isRunningRef.current) {
      console.log(`Sequence stopped before timeout, aborting`);
      return;
    }

    console.log(`Setting timeout for ${duration}ms (${duration/1000}s) before ${nextStep}`);
    timeoutRef.current = setTimeout(() => {
        // Check one more time before running next step (use ref for current value)
        if (isRunningRef.current) {
          runSequenceStep(nextStep);
        } else {
          console.log(`Sequence stopped, not running ${nextStep}`);
        }
    }, duration);
  };

  const toggleRun = async () => {
    if (isRunning) {
      stopSimulation();
    } else {
      // Sync config to Pi before starting sequence to ensure fan speed is current
      if (piIp && isPiOnline) {
        await handleSyncConfig();
      }
      isRunningRef.current = true;
      setIsRunning(true);
      runSequenceStep(MachineState.DIP);
    }
  };

  const [setups, setSetups] = useState<Record<string, any>>({});
  const [setupName, setSetupName] = useState<string>('');

  // Load setups from Pi
  const loadSetups = async () => {
    if (!piIp || !isPiOnline) return;
    try {
      const res = await fetch(`http://${piIp}:8080/list_setups`);
      if (res.ok) {
        const data = await res.json();
        if (data.success && data.setups) {
          setSetups(data.setups);
        }
      }
    } catch (e) {
      console.error("Failed to load setups:", e);
    }
  };

  // Save current setup
  const handleSaveSetup = async () => {
    if (!setupName.trim() || !piIp || !isPiOnline) return;
    try {
      const res = await fetch(`http://${piIp}:8080/save_setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: setupName.trim() }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setSetups(data.setups || {});
          setSetupName('');
          alert(`Setup "${setupName.trim()}" saved!`);
        }
      }
    } catch (e) {
      console.error("Failed to save setup:", e);
    }
  };

  // Load a setup
  const handleLoadSetup = async (name: string) => {
    if (!piIp || !isPiOnline) return;
    try {
      const res = await fetch(`http://${piIp}:8080/load_setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          alert(`Setup "${name}" loaded!`);
          // Reload motor positions
          window.location.reload(); // Simple refresh to reload positions
        } else {
          alert(`Failed to load setup: ${data.message || 'Unknown error'}`);
        }
      }
    } catch (e) {
      console.error("Failed to load setup:", e);
    }
  };

  // Delete a setup
  const handleDeleteSetup = async (name: string) => {
    if (!piIp || !isPiOnline) return;
    if (!confirm(`Delete setup "${name}"?`)) return;
    try {
      const res = await fetch(`http://${piIp}:8080/delete_setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setSetups(data.setups || {});
        }
      }
    } catch (e) {
      console.error("Failed to delete setup:", e);
    }
  };

  // Load setups when Pi comes online
  useEffect(() => {
    if (isPiOnline && piIp) {
      loadSetups();
    }
  }, [isPiOnline, piIp]);

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
      setMachineState(state);
    } else {
      // For BLOW toggle: don't change machine state, just toggle fan
      // Just stop the auto-sequence timer, but don't send IDLE
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      setIsRunning(false);
      // Don't change machineState for BLOW - keep current state
    }
    
    if (piIp && isPiOnline) {
      await handleSyncConfig();
      // sendRemoteCommand already handles updating fanRunning for BLOW state
      await sendRemoteCommand(state, false); // false = manual, not sequence
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
                setups={setups}
                setupName={setupName}
                setSetupName={setSetupName}
                onSaveSetup={handleSaveSetup}
                onLoadSetup={handleLoadSetup}
                onDeleteSetup={handleDeleteSetup}
              />
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
