
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
  const [piIp, setPiIp] = useState<string>(''); 
  const [config, setConfig] = useState<SimulationConfig>(DEFAULT_CONFIG);
  const [isSyncing, setIsSyncing] = useState(false);
  const [highlight, setHighlight] = useState<SystemHighlight>(null);
  const [isPiOnline, setIsPiOnline] = useState(false);
  
  const timeoutRef = useRef<any>(null);

  // Heartbeat check for Pi
  useEffect(() => {
    if (!piIp) {
      setIsPiOnline(false);
      return;
    }
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://${piIp}:5000/health`, { signal: AbortSignal.timeout(2000) });
        setIsPiOnline(res.ok);
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
      await fetch(`http://${piIp}:5000/set_state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state }),
      });
    } catch (e) {
      console.error("Failed to send command to Pi:", e);
    }
  };

  const handleSyncConfig = async () => {
    if (!piIp) return;
    setIsSyncing(true);
    try {
        await fetch(`http://${piIp}:5000/update_config`, {
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

  const handleManualState = (state: MachineState) => {
    stopSimulation();
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
