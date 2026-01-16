
import React, { useState, useEffect, useRef } from 'react';
import Schematic from './components/Schematic';
import ControlPanel from './components/ControlPanel';
import MultiTrackTimeline from './components/MultiTrackTimeline';
import { MachineState, DEFAULT_PINS, SimulationConfig, DEFAULT_CONFIG, TimelineBlock } from './types';
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
  const [currentTimelineIndex, setCurrentTimelineIndex] = useState<number>(0);
  const [currentPlaybackTime, setCurrentPlaybackTime] = useState<number>(0);
  
  const timeoutRefs = useRef<Map<string, any>>(new Map()); // Store all timeout refs by block ID
  const playbackIntervalRef = useRef<any>(null);
  const scheduledActionsRef = useRef<Map<number, TimelineBlock[]>>(new Map());
  const configLoadedRef = useRef<boolean>(false); // Track if config was just loaded from server
  const isRunningRef = useRef<boolean>(false); // Track running state for interval callbacks

  // Ensure loopTimeline is initialized
  useEffect(() => {
    if (!config.loopTimeline || config.loopTimeline.length === 0) {
      setConfig({
        ...config,
        loopTimeline: DEFAULT_CONFIG.loopTimeline,
        loopDuration: DEFAULT_CONFIG.loopDuration,
      });
    }
  }, []);

  // Auto-save timeline changes to server (debounced)
  useEffect(() => {
    if (!piIp || !isPiOnline || configLoadedRef.current) return;
    
    // Skip if this is the initial load (config just loaded from server)
    const timeoutId = setTimeout(async () => {
      try {
        await fetch(`http://${piIp}:8080/update_config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            loopTimeline: config.loopTimeline,
            loopDuration: config.loopDuration,
          }),
        });
      } catch (e) {
        console.error("Failed to save timeline to server:", e);
      }
    }, 1000); // Debounce: save 1 second after last change
    
    return () => clearTimeout(timeoutId);
  }, [config.loopTimeline, config.loopDuration, piIp, isPiOnline]);

  // Load config from server when Pi comes online
  useEffect(() => {
    if (piIp && isPiOnline && !configLoadedRef.current) {
      const loadConfig = async () => {
        try {
          const res = await fetch(`http://${piIp}:8080/get_config`, { signal: AbortSignal.timeout(2000) });
          if (res.ok) {
            const data = await res.json();
            if (data.success && data.config) {
              configLoadedRef.current = true;
              setConfig(data.config as SimulationConfig);
              // Reset flag after a delay to allow auto-save to work
              setTimeout(() => {
                configLoadedRef.current = false;
              }, 2000);
            }
          }
        } catch (e) {
          console.error("Failed to load config from server:", e);
        }
      };
      loadConfig();
    }
  }, [piIp, isPiOnline]);

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

  const stopSimulation = async (skipOpen = false) => {
    console.log("stopSimulation called, skipOpen:", skipOpen);
    
    // Set running to false FIRST to prevent any new blocks from executing
    setIsRunning(false);
    isRunningRef.current = false; // Update ref immediately for interval callbacks
    
    // Clear all scheduled timeouts
    timeoutRefs.current.forEach((timeout, blockId) => {
      if (timeout) {
        console.log(`Clearing timeout for block: ${blockId}`);
        clearTimeout(timeout);
      }
    });
    timeoutRefs.current.clear();
    
    if (playbackIntervalRef.current) {
      console.log("Clearing playback interval");
      clearInterval(playbackIntervalRef.current);
      playbackIntervalRef.current = null;
    }
    
    setCurrentTimelineIndex(0);
    setCurrentPlaybackTime(0);
    scheduledActionsRef.current.clear();
    
    console.log("All timeouts and intervals cleared, isRunning set to false");
    
    if (piIp && isPiOnline) {
      if (!skipOpen) {
        // Stop smoke first if running
        if (smokeRunning) {
          try {
            await fetch(`http://${piIp}:8080/control_smoke`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ action: 'stop' }),
            });
            setSmokeRunning(false);
            console.log("Stopped smoke machine");
          } catch (e) {
            console.error("Failed to stop smoke:", e);
          }
        }
        
        // Turn off fan
        try {
          await fetch(`http://${piIp}:8080/update_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fanEnabled: false }),
          });
          setFanRunning(false);
          console.log("Stopped fan");
        } catch (e) {
          console.error("Failed to stop fan:", e);
        }
        
        // Always send OPEN command - let server decide if movement is needed
        // This ensures arms return to home even if client-side position is stale
        // Wait a bit for fan/smoke to stop, then move arms
        await new Promise(resolve => setTimeout(resolve, 100)); // Small delay to let fan/smoke stop
        
        try {
          console.log("Sending OPEN command to return arms to home position");
          await sendRemoteCommand(MachineState.OPEN);
          setMachineState(MachineState.OPEN);
          console.log("OPEN command completed");
        } catch (e) {
          console.error("Failed to move arms to OPEN:", e);
          setMachineState(MachineState.IDLE);
        }
      } else {
        // Still stop fan and smoke even if skipping OPEN
        if (smokeRunning) {
          try {
            await fetch(`http://${piIp}:8080/control_smoke`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ action: 'stop' }),
            });
            setSmokeRunning(false);
          } catch (e) {
            console.error("Failed to stop smoke:", e);
          }
        }
        
        try {
          await fetch(`http://${piIp}:8080/update_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fanEnabled: false }),
          });
          setFanRunning(false);
        } catch (e) {
          console.error("Failed to stop fan:", e);
        }
      }
    } else {
      setMachineState(MachineState.IDLE);
    }
  };

  const sendRemoteCommand = async (state: MachineState) => {
    if (!piIp) return;
    try {
      console.log(`Sending remote command: ${state}`);
      const response = await fetch(`http://${piIp}:8080/set_state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ state }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log(`Command ${state} response:`, data);
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
      throw e; // Re-throw so caller knows it failed
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
    console.log(`handleSmokeControl called: action=${action}, piIp=${piIp}, isPiOnline=${isPiOnline}`);
    if (!piIp || !isPiOnline) {
      console.warn("Cannot control smoke: piIp or isPiOnline is false", { piIp, isPiOnline });
      return;
    }
    try {
      const requestBody = {
        action,
        intensity: config.smokeIntensity,
        duration: config.smokeDuration,
      };
      console.log(`Sending smoke control request:`, requestBody);
      const response = await fetch(`http://${piIp}:8080/control_smoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });
      console.log(`Smoke control response status:`, response.status);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log(`Smoke control response data:`, data);
      if (data.success) {
        setSmokeRunning(data.smoke_running || false);
        console.log(`Smoke ${action} successful, smokeRunning set to:`, data.smoke_running);
      } else {
        console.error("Smoke control failed:", data);
      }
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

  const executeBlock = (block: TimelineBlock) => {
    // Check if still running before executing (use ref for reliability)
    if (!isRunningRef.current) {
      console.log(`executeBlock: Skipping ${block.id} (${block.action}) - loop is stopped`);
      return;
    }
    
    console.log(`executeBlock: Executing ${block.id} (${block.action})`);
    // Execute block immediately without awaiting (non-blocking)
    switch (block.type) {
      case 'motor':
        const motorState = block.action as MachineState;
        setMachineState(motorState);
        
        // Calculate duration BEFORE updating position (needs current position)
        const motorDuration = calculateMovementDuration(motorState);
        setMovementDuration(motorDuration);
        
        // Update expected motor positions immediately so next block calculates correctly
        let targetA = motorAPosition;
        let targetB = motorBPosition;
        switch (motorState) {
          case MachineState.DIP:
            targetA = config.motorADipPosition || 200;
            targetB = config.motorBDipPosition || -200;
            break;
          case MachineState.OPEN:
          case MachineState.HOME:
            // OPEN/HOME always goes to (0, 0) - home position
            targetA = 0;
            targetB = 0;
            break;
          case MachineState.CLOSE:
            targetA = config.motorAClosePosition || 200;
            targetB = config.motorBClosePosition || -200;
            break;
        }
        // Update position state immediately so next block calculates from correct position
        setMotorAPosition(targetA);
        setMotorBPosition(targetB);
        
        if (piIp && isPiOnline) {
          // Don't await - let motor movement happen in background
          sendRemoteCommand(motorState).catch(e => {
            console.error("Failed to send motor command:", e);
          });
        }
        // Motor block duration represents wait time after movement
        // The actual movement duration is calculated, then we wait for block.duration
        // This is handled by the timeline's startTime positioning
        break;

      case 'fan':
        // Skip fan blocks - fan is controlled by toggle and stays on during loop if enabled
        console.log(`Skipping fan block ${block.id} - fan is controlled by toggle (always on if enabled)`);
        break;

      case 'smoke':
        if (block.action === 'start') {
          const smokeIntensity = block.config?.smokeIntensity || config.smokeIntensity;
          const smokeDuration = block.duration || config.smokeDuration;
          console.log(`Starting smoke: intensity=${smokeIntensity}, duration=${smokeDuration}`);
          if (piIp && isPiOnline) {
            // Don't await - execute immediately for accurate timing
            fetch(`http://${piIp}:8080/control_smoke`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                action: 'start',
                intensity: smokeIntensity,
                duration: smokeDuration,
              }),
            })
            .then(response => {
              console.log("Smoke start response:", response.status);
              return response.json();
            })
            .then(data => {
              console.log("Smoke start data:", data);
              if (data.success) {
                setSmokeRunning(true);
              }
            })
            .catch(e => console.error("Failed to start smoke:", e));
          } else {
            console.warn("Cannot start smoke: piIp or isPiOnline is false", { piIp, isPiOnline });
          }
        } else {
          console.log(`Stopping smoke`);
          if (piIp && isPiOnline) {
            // Don't await - execute immediately for accurate timing
            fetch(`http://${piIp}:8080/control_smoke`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ action: 'stop' }),
            })
            .then(() => setSmokeRunning(false))
            .catch(e => console.error("Failed to stop smoke:", e));
          }
        }
        break;
    }
  };

  const toggleRun = () => {
    if (isRunning) {
      stopSimulation();
    } else {
      const timeline = config.loopTimeline || [];
      if (timeline.length === 0) {
        console.warn("No blocks in timeline");
        return;
      }

      // Collect all blocks from all tracks and sort by startTime
      const allBlocks: Array<{ block: TimelineBlock; startTime: number }> = [];
      timeline.forEach(track => {
        track.blocks.forEach(block => {
          allBlocks.push({ block, startTime: block.startTime });
        });
      });
      allBlocks.sort((a, b) => a.startTime - b.startTime);

      if (allBlocks.length === 0) {
        console.warn("No blocks in timeline tracks");
        return;
      }

      // Calculate total loop duration
      let maxEndTime = 0;
      allBlocks.forEach(({ block }) => {
        let duration = block.duration;
        if (block.type === 'motor') {
          // Motor duration = movement duration + wait duration
          const movementDuration = calculateMovementDuration(block.action as MachineState);
          duration = movementDuration + block.duration;
        }
        const endTime = block.startTime + duration;
        if (endTime > maxEndTime) {
          maxEndTime = endTime;
        }
      });

      setIsRunning(true);
      isRunningRef.current = true; // Update ref for interval callbacks
      setCurrentPlaybackTime(0);
      scheduledActionsRef.current.clear();

      // Start fan if enabled (always on during loop)
      // Only send fanEnabled and fanSpeed to avoid sending full config that might have fanEnabled: false
      if (config.fanEnabled && piIp && isPiOnline) {
        fetch(`http://${piIp}:8080/update_config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ fanEnabled: true, fanSpeed: config.fanSpeed }),
        })
        .then(() => setFanRunning(true))
        .catch(e => console.error("Failed to start fan on loop start:", e));
      }

      // Schedule all blocks
      allBlocks.forEach(({ block, startTime }) => {
        const scheduleTime = Math.round(startTime * 1000);
        if (!scheduledActionsRef.current.has(scheduleTime)) {
          scheduledActionsRef.current.set(scheduleTime, []);
        }
        scheduledActionsRef.current.get(scheduleTime)!.push(block);
      });

      // Store loop data for restart
      const loopData = { allBlocks, maxEndTime };

      // Update playhead every 100ms
      playbackIntervalRef.current = setInterval(() => {
        // Check running state using ref (more reliable than state in callbacks)
        if (!isRunningRef.current) {
          return; // Stop updating if not running
        }
        
        setCurrentPlaybackTime(prev => {
          const newTime = prev + 0.1;
          // Check if we've reached the end of the loop
          if (newTime >= loopData.maxEndTime) {
            // Double-check we're still running before re-scheduling
            if (isRunningRef.current) {
              console.log("Loop completed, restarting blocks");
              // Re-execute all blocks for next loop iteration
              loopData.allBlocks.forEach(({ block, startTime }) => {
                const scheduleTime = startTime * 1000; // Convert to milliseconds
                const timeoutId = setTimeout(() => {
                  // Final check before executing
                  if (isRunningRef.current) {
                    console.log(`Executing block ${block.id} (${block.action})`);
                    executeBlock(block);
                  } else {
                    console.log(`Skipping block ${block.id} - loop stopped`);
                  }
                  timeoutRefs.current.delete(block.id);
                }, scheduleTime);
                timeoutRefs.current.set(block.id, timeoutId);
              });
            } else {
              console.log("Loop end reached but not running, skipping restart");
            }
            return 0;
          }
          return newTime;
        });
      }, 100);

      // Execute blocks at their scheduled times
      // Use performance.now() for more accurate timing
      const loopStartTime = performance.now();
      allBlocks.forEach(({ block, startTime }) => {
        const scheduleTime = startTime * 1000; // Convert to milliseconds
        const timeoutId = setTimeout(() => {
          // Execute block at exact startTime
          executeBlock(block);
          // Remove timeout ref after execution
          timeoutRefs.current.delete(block.id);
        }, scheduleTime);
        timeoutRefs.current.set(block.id, timeoutId);
      });
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
            // OPEN/HOME always goes to (0, 0) - home position
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
    stopSimulation(true); // Skip OPEN command - we're switching to manual control
    
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
        
        <div className="lg:col-span-8 flex flex-col gap-4 h-full min-h-0">
          <div className="flex-1 bg-slate-900 rounded-xl border border-slate-800 shadow-2xl overflow-hidden relative min-h-0">
            <div className="absolute inset-0">
               <Schematic activeState={machineState} fanSpeed={config.fanSpeed} fanEnabled={config.fanEnabled} fanRunning={fanRunning} highlight={null} motorAPosition={motorAPosition} motorBPosition={motorBPosition} movementDuration={movementDuration} />
            </div>
          </div>
          
          {/* Multi-Track Timeline */}
          <div className="flex-none rounded-xl border border-slate-800 shadow-xl bg-slate-900 p-4">
            <MultiTrackTimeline 
              config={config}
              setConfig={setConfig}
              isRunning={isRunning}
              motorAPosition={motorAPosition}
              motorBPosition={motorBPosition}
              currentTime={currentPlaybackTime}
            />
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
