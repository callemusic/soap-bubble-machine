import React, { useState, useRef, useEffect } from 'react';
import { TimelineBlock, TimelineTrack, TimelineTrackType, SimulationConfig } from '../types';
import { GripVertical, Plus, Trash2, MoveVertical, Wind, Cloud, Play, Square } from 'lucide-react';

interface MultiTrackTimelineProps {
  config: SimulationConfig;
  setConfig: (config: SimulationConfig) => void;
  isRunning: boolean;
  motorAPosition: number;
  motorBPosition: number;
  currentTime?: number; // Current playback time for playhead
}

const TRACK_HEIGHT = 60;
const TIME_SCALE = 50; // pixels per second
const MIN_BLOCK_WIDTH = 40;
const MIN_MOTOR_BLOCK_WIDTH = 100; // Motor blocks need more space for dropdown + duration
const TRACK_LABEL_WIDTH = 96; // w-24 = 96px (24 * 4px)

const MultiTrackTimeline: React.FC<MultiTrackTimelineProps> = ({ 
  config, 
  setConfig, 
  isRunning, 
  motorAPosition,
  motorBPosition,
  currentTime = 0,
}) => {
  const [draggedBlockId, setDraggedBlockId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState<number>(0);
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<string>('');
  const [editingType, setEditingType] = useState<'duration' | 'config' | null>(null);
  const [resizingBlockId, setResizingBlockId] = useState<string | null>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState<number>(1); // Zoom level for timeline

  const timeline = config.loopTimeline || [];
  const totalDuration = config.loopDuration || 10;

  // Clean up misplaced blocks on mount
  useEffect(() => {
    let needsCleanup = false;
    const cleanedTimeline = timeline.map(track => {
      const correctBlocks = track.blocks.filter(block => {
        if (track.type === 'motors' && block.type !== 'motor') {
          needsCleanup = true;
          return false;
        }
        if (track.type === 'fan' && block.type !== 'fan') {
          needsCleanup = true;
          return false;
        }
        if (track.type === 'smoke' && block.type !== 'smoke') {
          needsCleanup = true;
          return false;
        }
        return true;
      });
      return { ...track, blocks: correctBlocks };
    });

    if (needsCleanup) {
      // Calculate new duration after cleanup
      let maxEnd = 0;
      cleanedTimeline.forEach(track => {
        track.blocks.forEach(block => {
          let duration = block.duration;
          if (block.type === 'motor') {
            duration = calculateMotorDuration(block.action) + block.duration;
          }
          const endTime = block.startTime + duration;
          if (endTime > maxEnd) {
            maxEnd = endTime;
          }
        });
      });
      setConfig({ ...config, loopTimeline: cleanedTimeline, loopDuration: maxEnd });
    }
  }, []); // Only run on mount

  const calculateMotorDuration = (action: string): number => {
    const stepDelay = 0.002;
    let targetA = 0;
    let targetB = 0;
    
    switch (action) {
      case 'DIP':
        targetA = config.motorADipPosition || 200;
        targetB = config.motorBDipPosition || -200;
        break;
      case 'OPEN':
        targetA = 0;
        targetB = 0;
        break;
      case 'CLOSE':
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

  const getBlockColor = (block: TimelineBlock): string => {
    switch (block.type) {
      case 'motor':
        return 'bg-blue-600';
      case 'fan':
        return block.action === 'start' ? 'bg-green-600' : 'bg-red-600';
      case 'smoke':
        return block.action === 'start' ? 'bg-purple-600' : 'bg-orange-600';
      default:
        return 'bg-slate-600';
    }
  };

  const getBlockLabel = (block: TimelineBlock): string => {
    switch (block.type) {
      case 'motor':
        return block.action;
      case 'fan':
        return block.action === 'start' 
          ? `Fan ON`
          : 'Fan OFF';
      case 'smoke':
        return block.action === 'start'
          ? `Smoke ON`
          : 'Smoke OFF';
      default:
        return '';
    }
  };

  const getBlockIcon = (block: TimelineBlock) => {
    switch (block.type) {
      case 'motor':
        return <MoveVertical size={12} />;
      case 'fan':
        return <Wind size={12} />;
      case 'smoke':
        return <Cloud size={12} />;
      default:
        return null;
    }
  };

  const getBlockWidth = (block: TimelineBlock): number => {
    let duration = block.duration;
    const minWidth = block.type === 'motor' ? MIN_MOTOR_BLOCK_WIDTH : MIN_BLOCK_WIDTH;
    if (block.type === 'motor') {
      // For motors: movement duration + wait duration
      const movementDuration = calculateMotorDuration(block.action);
      duration = movementDuration + block.duration; // block.duration is wait time after movement
    } else if (block.type === 'fan' && block.action === 'start') {
      // For fan start blocks, duration is visual only (fan stops via stop block)
      // Use a minimum visual width so the block is visible
      duration = Math.max(block.duration, 0.5); // At least 0.5s visual width
    }
    return Math.max(minWidth, duration * TIME_SCALE * zoom);
  };

  const handleMouseDown = (e: React.MouseEvent, block: TimelineBlock, trackId: string) => {
    if (isRunning) return;
    e.preventDefault();
    setDraggedBlockId(block.id);
    // Get the block's container (the one with left-24 offset)
    const blockElement = e.currentTarget.closest('[style*="left: 24"]') as HTMLElement;
    if (blockElement) {
      const blockRect = blockElement.getBoundingClientRect();
      const x = e.clientX - blockRect.left;
      // Calculate offset from block's start position
      const dragOffset = (x / (TIME_SCALE * zoom)) - block.startTime;
      setDragOffset(dragOffset);
    } else {
      // Fallback: calculate relative to timeline container
      const rect = timelineRef.current?.getBoundingClientRect();
      if (rect) {
        const x = e.clientX - rect.left - TRACK_LABEL_WIDTH;
        const dragOffset = (x / (TIME_SCALE * zoom)) - block.startTime;
        setDragOffset(dragOffset);
      }
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draggedBlockId || !timelineRef.current) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - TRACK_LABEL_WIDTH;
    const newStartTime = Math.max(0, (x / (TIME_SCALE * zoom)) - dragOffset);
    
    const newTimeline = timeline.map(track => ({
      ...track,
      blocks: track.blocks.map(block => 
        block.id === draggedBlockId 
          ? { ...block, startTime: newStartTime }
          : block
      ),
    }));
    
    // Calculate new duration
    let maxEnd = 0;
    newTimeline.forEach(track => {
      track.blocks.forEach(block => {
        let duration = block.duration;
        if (block.type === 'motor') {
          duration = calculateMotorDuration(block.action) + block.duration;
        }
        const endTime = block.startTime + duration;
        if (endTime > maxEnd) {
          maxEnd = endTime;
        }
      });
    });
    
    setConfig({ ...config, loopTimeline: newTimeline, loopDuration: maxEnd });
  };

  const handleMouseUp = () => {
    setDraggedBlockId(null);
    setDragOffset(0);
    setResizingBlockId(null);
  };

  useEffect(() => {
    if (draggedBlockId) {
      const handleGlobalMouseMove = (e: MouseEvent) => {
        if (!timelineRef.current) return;
        const rect = timelineRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left - TRACK_LABEL_WIDTH;
        const newStartTime = Math.max(0, (x / (TIME_SCALE * zoom)) - dragOffset);
        
        const newTimeline = timeline.map(track => ({
          ...track,
          blocks: track.blocks.map(block => 
            block.id === draggedBlockId 
              ? { ...block, startTime: newStartTime }
              : block
          ),
        }));
        
        // Calculate new duration
        let maxEnd = 0;
        newTimeline.forEach(track => {
          track.blocks.forEach(block => {
            let duration = block.duration;
            if (block.type === 'motor') {
              duration = calculateMotorDuration(block.action) + block.duration;
            }
            const endTime = block.startTime + duration;
            if (endTime > maxEnd) {
              maxEnd = endTime;
            }
          });
        });
        
        setConfig({ ...config, loopTimeline: newTimeline, loopDuration: maxEnd });
      };

      const handleGlobalMouseUp = () => {
        handleMouseUp();
      };

      window.addEventListener('mousemove', handleGlobalMouseMove);
      window.addEventListener('mouseup', handleGlobalMouseUp);
      
      return () => {
        window.removeEventListener('mousemove', handleGlobalMouseMove);
        window.removeEventListener('mouseup', handleGlobalMouseUp);
      };
    }
  }, [draggedBlockId, dragOffset, zoom, timeline, config]);

  const handleAddBlock = (trackId: string, trackType: TimelineTrackType) => {
    const track = timeline.find(t => t.id === trackId);
    if (!track) return;

    let newBlock: TimelineBlock;
    const lastBlock = track.blocks[track.blocks.length - 1];
    // Calculate startTime: if no blocks, start at 0; otherwise start after last block's end time
    let startTime = 0;
    if (lastBlock) {
      let lastBlockDuration = lastBlock.duration;
      if (lastBlock.type === 'motor') {
        // For motors: movement duration + wait duration
        lastBlockDuration = calculateMotorDuration(lastBlock.action) + lastBlock.duration;
      }
      startTime = lastBlock.startTime + lastBlockDuration;
    }

    switch (trackType) {
      case 'motors':
        newBlock = {
          id: Date.now().toString(),
          type: 'motor',
          action: 'OPEN',
          startTime,
          duration: 0,
        };
        break;
      case 'fan':
        newBlock = {
          id: Date.now().toString(),
          type: 'fan',
          action: 'start',
          startTime,
          duration: 3.0,
          config: { fanSpeed: config.fanSpeed },
        };
        break;
      case 'smoke':
        newBlock = {
          id: Date.now().toString(),
          type: 'smoke',
          action: 'start',
          startTime,
          duration: 0.5, // Default smoke duration: 0.5 seconds
          config: { smokeIntensity: config.smokeIntensity },
        };
        break;
    }

    const newTimeline = timeline.map(t =>
      t.id === trackId
        ? { ...t, blocks: [...t.blocks, newBlock] }
        : t
    );

    // Calculate new duration
    let maxEnd = 0;
    newTimeline.forEach(track => {
      track.blocks.forEach(block => {
        let duration = block.duration;
        if (block.type === 'motor') {
          duration = calculateMotorDuration(block.action) + block.duration;
        }
        const endTime = block.startTime + duration;
        if (endTime > maxEnd) {
          maxEnd = endTime;
        }
      });
    });

    setConfig({ ...config, loopTimeline: newTimeline, loopDuration: maxEnd });
  };

  const handleDeleteBlock = (blockId: string) => {
    const newTimeline = timeline.map(track => ({
      ...track,
      blocks: track.blocks.filter(b => b.id !== blockId),
    }));
    
    // Calculate new duration
    let maxEnd = 0;
    newTimeline.forEach(track => {
      track.blocks.forEach(block => {
        let duration = block.duration;
        if (block.type === 'motor') {
          duration = calculateMotorDuration(block.action) + block.duration;
        }
        const endTime = block.startTime + duration;
        if (endTime > maxEnd) {
          maxEnd = endTime;
        }
      });
    });
    
    setConfig({ ...config, loopTimeline: newTimeline, loopDuration: maxEnd });
  };

  const handleDurationClick = (block: TimelineBlock) => {
    // Don't allow editing duration for fan start blocks - duration is controlled by stop block position
    if (block.type === 'fan' && block.action === 'start') {
      return; // Duration is visual only, actual stop is controlled by stop block
    }
    // Allow editing duration for all other block types
    // For motors, this represents a wait/delay after movement completes
    setEditingBlockId(block.id);
    setEditingType('duration');
    setEditingValue(block.duration.toString());
  };

  const handleConfigClick = (block: TimelineBlock) => {
    if (block.type === 'fan' && block.action === 'start') {
      setEditingBlockId(block.id);
      setEditingType('config');
      setEditingValue((block.config?.fanSpeed || config.fanSpeed).toString());
    } else if (block.type === 'smoke' && block.action === 'start') {
      setEditingBlockId(block.id);
      setEditingType('config');
      setEditingValue((block.config?.smokeIntensity || config.smokeIntensity).toString());
    }
  };

  const handleChangeAction = (blockId: string, newAction: string) => {
    const newTimeline = timeline.map(track => ({
      ...track,
      blocks: track.blocks.map(block =>
        block.id === blockId ? { ...block, action: newAction } : block
      ),
    }));
    
    // Calculate new duration
    let maxEnd = 0;
    newTimeline.forEach(track => {
      track.blocks.forEach(block => {
        let duration = block.duration;
        if (block.type === 'motor') {
          duration = calculateMotorDuration(block.action) + block.duration;
        }
        const endTime = block.startTime + duration;
        if (endTime > maxEnd) {
          maxEnd = endTime;
        }
      });
    });
    
    setConfig({ ...config, loopTimeline: newTimeline, loopDuration: maxEnd });
  };

  const updateBlock = (blockId: string, updates: Partial<TimelineBlock>) => {
    const newTimeline = timeline.map(track => ({
      ...track,
      blocks: track.blocks.map(block =>
        block.id === blockId ? { ...block, ...updates } : block
      ),
    }));
    // Calculate new duration
    let maxEnd = 0;
    newTimeline.forEach(track => {
      track.blocks.forEach(block => {
        let duration = block.duration;
        if (block.type === 'motor') {
          duration = calculateMotorDuration(block.action) + block.duration;
        }
        const endTime = block.startTime + duration;
        if (endTime > maxEnd) {
          maxEnd = endTime;
        }
      });
    });
    setConfig({ ...config, loopTimeline: newTimeline, loopDuration: maxEnd });
  };

  const handleEditBlur = () => {
    if (editingBlockId && editingType) {
      const numValue = parseFloat(editingValue);
      if (!isNaN(numValue) && numValue >= 0) {
        if (editingType === 'duration') {
          updateBlock(editingBlockId, { duration: numValue });
        } else if (editingType === 'config') {
          const block = timeline.flatMap(t => t.blocks).find(b => b.id === editingBlockId);
          if (block?.type === 'fan') {
            updateBlock(editingBlockId, { config: { ...block.config, fanSpeed: numValue } });
          } else if (block?.type === 'smoke') {
            updateBlock(editingBlockId, { config: { ...block.config, smokeIntensity: numValue } });
          }
        }
      }
    }
    setEditingBlockId(null);
    setEditingType(null);
    setEditingValue('');
  };

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleEditBlur();
    }
  };

  // Calculate total duration from all blocks
  const calculateTotalDuration = (): number => {
    let maxEnd = 0;
    timeline.forEach(track => {
      track.blocks.forEach(block => {
        let duration = block.duration;
        if (block.type === 'motor') {
          // Motor duration = movement duration + wait duration
          duration = calculateMotorDuration(block.action) + block.duration;
        }
        const endTime = block.startTime + duration;
        if (endTime > maxEnd) {
          maxEnd = endTime;
        }
      });
    });
    return maxEnd;
  };

  const actualDuration = calculateTotalDuration();
  const timelineWidth = Math.max(actualDuration * TIME_SCALE * zoom, 800);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-tighter">Loop Timeline</h4>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-[10px] text-slate-300"
            >
              −
            </button>
            <span className="text-[10px] text-slate-500 w-12 text-center">
              {Math.round(zoom * 100)}%
            </span>
            <button
              onClick={() => setZoom(Math.min(2, zoom + 0.25))}
              className="px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-[10px] text-slate-300"
            >
              +
            </button>
          </div>
          <span className="text-[10px] text-slate-500">
            Total: <span className="text-blue-400 font-mono">{actualDuration.toFixed(1)}s</span>
          </span>
        </div>
      </div>

      <div className="bg-slate-950 border border-slate-800 rounded overflow-hidden">
        {/* Single scroll container for both ruler and tracks */}
        <div className="overflow-x-auto">
          <div
            ref={timelineRef}
            className="relative"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            style={{ width: `${timelineWidth + TRACK_LABEL_WIDTH}px`, minWidth: '100%' }}
          >
            {/* Time ruler */}
            <div className="relative h-6 bg-slate-900 border-b border-slate-800">
              {/* Track label spacer to align with tracks below */}
              <div className="absolute left-0 top-0 bottom-0 w-24 bg-slate-900 border-r border-slate-800" />
              {/* Time markers - offset by track label width */}
              <div className="absolute left-24 right-0 top-0 bottom-0" style={{ width: `${timelineWidth}px` }}>
                {Array.from({ length: Math.ceil(actualDuration) + 1 }).map((_, i) => (
                  <div
                    key={i}
                    className="absolute border-l border-slate-700"
                    style={{ left: `${i * TIME_SCALE * zoom}px` }}
                  >
                    <span className="absolute top-0 left-1 text-[9px] text-slate-500">{i}s</span>
                  </div>
                ))}
                {/* Playhead */}
                {isRunning && (
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10"
                    style={{ left: `${currentTime * TIME_SCALE * zoom}px` }}
                  >
                    <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-red-500" />
                  </div>
                )}
              </div>
            </div>

            {/* Tracks */}
          {timeline.map((track, trackIndex) => (
            <div
              key={track.id}
              className="relative border-b border-slate-800"
              style={{ height: `${TRACK_HEIGHT}px` }}
            >
              {/* Track label */}
              <div className="absolute left-0 top-0 bottom-0 w-24 bg-slate-900 border-r border-slate-800 flex items-center justify-between px-2 z-20">
                <div className="flex items-center gap-1.5">
                  {track.type === 'motors' && <MoveVertical size={12} className="text-blue-400" />}
                  {track.type === 'fan' && <Wind size={12} className="text-green-400" />}
                  {track.type === 'smoke' && <Cloud size={12} className="text-purple-400" />}
                  <span className="text-[10px] font-bold text-slate-300">{track.name}</span>
                </div>
                {!isRunning && (
                  <button
                    onClick={() => handleAddBlock(track.id, track.type)}
                    className="p-0.5 hover:bg-slate-800 rounded text-slate-400 hover:text-white transition-colors"
                    title={`Add ${track.name} block`}
                  >
                    <Plus size={10} />
                  </button>
                )}
              </div>

              {/* Blocks */}
              <div className="absolute left-24 right-0 top-0 bottom-0">
                {track.blocks
                  .filter(block => {
                    // Ensure blocks match their track type
                    if (track.type === 'motors' && block.type !== 'motor') return false;
                    if (track.type === 'fan' && block.type !== 'fan') return false;
                    if (track.type === 'smoke' && block.type !== 'smoke') return false;
                    return true;
                  })
                  .map((block) => {
                  const blockWidth = getBlockWidth(block);
                  const isDragging = draggedBlockId === block.id;
                  // For display: show movement duration for motors, or total duration (movement + wait)
                  const displayDuration = block.type === 'motor' 
                    ? calculateMotorDuration(block.action) + block.duration
                    : block.duration;
                  const movementDuration = block.type === 'motor'
                    ? calculateMotorDuration(block.action)
                    : 0;

                  return (
                    <div
                      key={block.id}
                      className={`
                        absolute top-1 bottom-1 rounded border-2 transition-all group
                        ${getBlockColor(block)}
                        ${isDragging ? 'opacity-50 z-30' : 'z-10'}
                        ${!isRunning ? 'cursor-move hover:scale-y-105' : 'cursor-default'}
                      `}
                      style={{
                        left: `${block.startTime * TIME_SCALE * zoom}px`,
                        width: `${blockWidth}px`,
                      }}
                      onMouseDown={(e) => handleMouseDown(e, block, track.id)}
                    >
                      <div className="h-full flex items-center gap-1 px-1.5 text-white">
                        {!isRunning && (
                          <GripVertical size={10} className="text-white/50 group-hover:text-white" />
                        )}
                        {getBlockIcon(block)}
                        {block.type === 'motor' ? (
                          <select
                            value={block.action}
                            onChange={(e) => handleChangeAction(block.id, e.target.value)}
                            className="text-[9px] font-bold bg-white/20 border border-white/30 rounded px-1 py-0.5 outline-none cursor-pointer"
                            onClick={(e) => e.stopPropagation()}
                            onMouseDown={(e) => e.stopPropagation()}
                          >
                            <option value="OPEN">OPEN</option>
                            <option value="CLOSE">CLOSE</option>
                            <option value="DIP">DIP</option>
                          </select>
                        ) : block.type === 'fan' || block.type === 'smoke' ? (
                          <select
                            value={block.action}
                            onChange={(e) => handleChangeAction(block.id, e.target.value)}
                            className="text-[9px] font-bold bg-white/20 border border-white/30 rounded px-1 py-0.5 outline-none cursor-pointer"
                            onClick={(e) => e.stopPropagation()}
                            onMouseDown={(e) => e.stopPropagation()}
                          >
                            <option value="start">Start</option>
                            <option value="stop">Stop</option>
                          </select>
                        ) : (
                          <span className="text-[9px] font-bold">{getBlockLabel(block)}</span>
                        )}
                        <div className="flex-1" />
                        {block.type === 'fan' && block.action === 'start' && (
                          <span
                            className="text-[8px] text-white/70 cursor-pointer hover:text-white"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleConfigClick(block);
                            }}
                            title="Click to edit fan speed"
                          >
                            {editingBlockId === block.id && editingType === 'config' ? (
                              <input
                                type="number"
                                step="1"
                                min="0"
                                max="100"
                                value={editingValue}
                                onChange={(e) => setEditingValue(e.target.value)}
                                onBlur={handleEditBlur}
                                onKeyDown={handleEditKeyDown}
                                className="w-8 bg-white/20 text-white text-[8px] px-1 rounded border border-white/30 outline-none"
                                autoFocus
                              />
                            ) : (
                              `${block.config?.fanSpeed || config.fanSpeed}%`
                            )}
                          </span>
                        )}
                        {block.type === 'smoke' && block.action === 'start' && (
                          <span
                            className="text-[8px] text-white/70 cursor-pointer hover:text-white"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleConfigClick(block);
                            }}
                            title="Click to edit smoke intensity"
                          >
                            {editingBlockId === block.id && editingType === 'config' ? (
                              <input
                                type="number"
                                step="1"
                                min="0"
                                max="127"
                                value={editingValue}
                                onChange={(e) => setEditingValue(e.target.value)}
                                onBlur={handleEditBlur}
                                onKeyDown={handleEditKeyDown}
                                className="w-8 bg-white/20 text-white text-[8px] px-1 rounded border border-white/30 outline-none"
                                autoFocus
                              />
                            ) : (
                              `${block.config?.smokeIntensity || config.smokeIntensity}`
                            )}
                          </span>
                        )}
                        <span
                          className={`text-[8px] text-white/70 font-mono ${
                            block.type === 'fan' && block.action === 'start' 
                              ? 'cursor-default' 
                              : 'cursor-pointer hover:text-white'
                          }`}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (!(block.type === 'fan' && block.action === 'start')) {
                              handleDurationClick(block);
                            }
                          }}
                          title={
                            block.type === 'motor' 
                              ? 'Click to add wait/delay after motor movement (movement duration is calculated automatically)' 
                              : block.type === 'fan' && block.action === 'start'
                              ? 'Duration is visual only - fan stops when stop block executes'
                              : 'Click to edit duration'
                          }
                        >
                          {editingBlockId === block.id && editingType === 'duration' ? (
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              value={editingValue}
                              onChange={(e) => setEditingValue(e.target.value)}
                              onBlur={handleEditBlur}
                              onKeyDown={handleEditKeyDown}
                              className="w-10 bg-white/20 text-white text-[8px] px-1 rounded border border-white/30 outline-none"
                              autoFocus
                            />
                          ) : block.type === 'motor' ? (
                            <span title={`Movement: ${movementDuration.toFixed(1)}s + Wait: ${block.duration.toFixed(1)}s`}>
                              {displayDuration.toFixed(1)}s
                            </span>
                          ) : block.type === 'fan' && block.action === 'start' ? (
                            <span title="Visual duration - fan stops when stop block executes">
                              {displayDuration.toFixed(1)}s
                            </span>
                          ) : (
                            `${displayDuration.toFixed(1)}s`
                          )}
                        </span>
                        {!isRunning && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteBlock(block.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-red-600 rounded"
                            title="Delete block"
                          >
                            <Trash2 size={8} className="text-white" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
          </div>
        </div>
      </div>

      {timeline.length > 0 && (
        <div className="text-[9px] text-slate-500 text-center">
          Drag blocks to move in time • Click duration/config to edit • Hover to delete
        </div>
      )}
    </div>
  );
};

export default MultiTrackTimeline;
