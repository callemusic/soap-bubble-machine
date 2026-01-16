import React, { useState, useRef, useEffect } from 'react';
import { TimelineBlock, TimelineBlockType, SimulationConfig } from '../types';
import { GripVertical, Plus, Trash2, Clock, MoveVertical, Wind, Cloud, Pause } from 'lucide-react';

interface LoopTimelineProps {
  config: SimulationConfig;
  setConfig: (config: SimulationConfig) => void;
  isRunning: boolean;
  motorAPosition: number;
  motorBPosition: number;
}

const LoopTimeline: React.FC<LoopTimelineProps> = ({ config, setConfig, isRunning, motorAPosition, motorBPosition }) => {
  const [draggedBlockId, setDraggedBlockId] = useState<string | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);
  const [editingDuration, setEditingDuration] = useState<string>('');
  const [editingConfig, setEditingConfig] = useState<string>('');
  const timelineRef = useRef<HTMLDivElement>(null);

  const timeline = config.loopTimeline || [];

  const calculateTotalDuration = (): number => {
    return timeline.reduce((total, block) => {
      if (block.type === 'motor') {
        // Motor duration is calculated dynamically based on movement
        return total;
      }
      return total + block.duration;
    }, 0);
  };

  const calculateMotorDuration = (action: string): number => {
    // Calculate duration based on current position and target position
    const stepDelay = 0.002; // seconds per step
    
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
      case 'wait':
        return 'bg-slate-700';
      case 'fan':
        return block.action === 'start' ? 'bg-green-600' : 'bg-red-600';
      case 'smoke':
        return block.action === 'start' ? 'bg-purple-600' : 'bg-orange-600';
      default:
        return 'bg-slate-600';
    }
  };

  const getBlockIcon = (block: TimelineBlock) => {
    switch (block.type) {
      case 'motor':
        return <MoveVertical size={14} />;
      case 'wait':
        return <Pause size={14} />;
      case 'fan':
        return <Wind size={14} />;
      case 'smoke':
        return <Cloud size={14} />;
      default:
        return null;
    }
  };

  const getBlockLabel = (block: TimelineBlock): string => {
    switch (block.type) {
      case 'motor':
        return block.action;
      case 'wait':
        return `${block.duration.toFixed(1)}s`;
      case 'fan':
        return block.action === 'start' 
          ? `Fan ON (${block.config?.fanSpeed || config.fanSpeed}%)`
          : 'Fan OFF';
      case 'smoke':
        return block.action === 'start'
          ? `Smoke ON (${block.config?.smokeIntensity || config.smokeIntensity})`
          : 'Smoke OFF';
      default:
        return '';
    }
  };

  const handleDragStart = (e: React.DragEvent, blockId: string) => {
    setDraggedBlockId(blockId);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverIndex(index);
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    if (draggedBlockId === null) return;

    const newTimeline = [...timeline];
    const draggedIndex = newTimeline.findIndex(b => b.id === draggedBlockId);
    if (draggedIndex === -1) return;

    const [draggedBlock] = newTimeline.splice(draggedIndex, 1);
    newTimeline.splice(dropIndex, 0, draggedBlock);

    setConfig({ ...config, loopTimeline: newTimeline });
    setDraggedBlockId(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedBlockId(null);
    setDragOverIndex(null);
  };

  const handleDeleteBlock = (blockId: string) => {
    const newTimeline = timeline.filter(b => b.id !== blockId);
    setConfig({ ...config, loopTimeline: newTimeline });
  };

  const handleAddBlock = (type: TimelineBlockType) => {
    const newBlock: TimelineBlock = {
      id: Date.now().toString(),
      type,
      action: type === 'motor' ? 'OPEN' : type === 'fan' ? 'start' : type === 'smoke' ? 'start' : 'wait',
      duration: type === 'wait' ? 1.0 : type === 'fan' ? 3.0 : type === 'smoke' ? 3.0 : 0,
      config: type === 'fan' ? { fanSpeed: config.fanSpeed } : type === 'smoke' ? { smokeIntensity: config.smokeIntensity } : undefined,
    };
    setConfig({ ...config, loopTimeline: [...timeline, newBlock] });
  };

  const handleChangeAction = (blockId: string, newAction: string) => {
    const newTimeline = timeline.map(block => {
      if (block.id === blockId) {
        return { ...block, action: newAction };
      }
      return block;
    });
    setConfig({ ...config, loopTimeline: newTimeline });
  };

  const handleDurationClick = (block: TimelineBlock) => {
    if (block.type === 'motor') return; // Motor duration is calculated
    setEditingBlockId(block.id);
    setEditingDuration(block.duration.toString());
  };

  const handleDurationChange = (blockId: string, value: string) => {
    const numValue = parseFloat(value);
    if (isNaN(numValue) || numValue < 0) return;
    
    const newTimeline = timeline.map(block => 
      block.id === blockId 
        ? { ...block, duration: numValue }
        : block
    );
    setConfig({ ...config, loopTimeline: newTimeline });
  };

  const handleDurationBlur = () => {
    setEditingBlockId(null);
    setEditingDuration('');
    setEditingConfig('');
  };

  const handleDurationKeyDown = (e: React.KeyboardEvent, blockId: string) => {
    if (e.key === 'Enter') {
      handleDurationBlur();
    }
  };

  const handleConfigClick = (block: TimelineBlock) => {
    if (block.type === 'fan' && block.action === 'start') {
      setEditingBlockId(block.id);
      setEditingConfig((block.config?.fanSpeed || config.fanSpeed).toString());
    } else if (block.type === 'smoke' && block.action === 'start') {
      setEditingBlockId(block.id);
      setEditingConfig((block.config?.smokeIntensity || config.smokeIntensity).toString());
    }
  };

  const handleConfigChange = (blockId: string, value: string) => {
    const numValue = parseFloat(value);
    if (isNaN(numValue) || numValue < 0) return;
    
    const newTimeline = timeline.map(block => {
      if (block.id === blockId) {
        if (block.type === 'fan' && block.action === 'start') {
          return { ...block, config: { ...block.config, fanSpeed: numValue } };
        } else if (block.type === 'smoke' && block.action === 'start') {
          return { ...block, config: { ...block.config, smokeIntensity: numValue } };
        }
      }
      return block;
    });
    setConfig({ ...config, loopTimeline: newTimeline });
  };

  const getBlockWidth = (block: TimelineBlock): number => {
    if (block.type === 'motor') {
      const duration = calculateMotorDuration(block.action);
      return Math.max(60, duration * 50); // Scale: 50px per second
    }
    return Math.max(60, block.duration * 50);
  };

  const totalDuration = calculateTotalDuration();
  const motorDurations = timeline
    .filter(b => b.type === 'motor')
    .reduce((sum, b) => sum + calculateMotorDuration(b.action), 0);
  const actualTotal = totalDuration + motorDurations;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-tighter">Loop Timeline</h4>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500">
            Total: <span className="text-blue-400 font-mono">{actualTotal.toFixed(1)}s</span>
          </span>
          {!isRunning && (
            <div className="flex gap-1">
              <button
                onClick={() => handleAddBlock('motor')}
                className="p-1 bg-blue-600 hover:bg-blue-500 rounded text-white text-[10px] transition-all"
                title="Add Motor Movement"
              >
                <MoveVertical size={12} />
              </button>
              <button
                onClick={() => handleAddBlock('wait')}
                className="p-1 bg-slate-700 hover:bg-slate-600 rounded text-white text-[10px] transition-all"
                title="Add Wait"
              >
                <Pause size={12} />
              </button>
              <button
                onClick={() => handleAddBlock('fan')}
                className="p-1 bg-green-600 hover:bg-green-500 rounded text-white text-[10px] transition-all"
                title="Add Fan Control"
              >
                <Wind size={12} />
              </button>
              <button
                onClick={() => handleAddBlock('smoke')}
                className="p-1 bg-purple-600 hover:bg-purple-500 rounded text-white text-[10px] transition-all"
                title="Add Smoke Control"
              >
                <Cloud size={12} />
              </button>
            </div>
          )}
        </div>
      </div>

      <div 
        ref={timelineRef}
        className="relative bg-slate-950 border border-slate-800 rounded p-3 min-h-[120px] overflow-x-auto"
      >
        {timeline.length === 0 ? (
          <div className="flex items-center justify-center h-20 text-slate-500 text-sm">
            No blocks in timeline. Click + buttons above to add actions.
          </div>
        ) : (
          <div className="flex items-center gap-2 flex-wrap">
            {timeline.map((block, index) => {
              const isDragging = draggedBlockId === block.id;
              const isDragOver = dragOverIndex === index;
              const blockWidth = getBlockWidth(block);
              const isEditing = editingBlockId === block.id;
              const duration = block.type === 'motor' 
                ? calculateMotorDuration(block.action) 
                : block.duration;

              return (
                <div
                  key={block.id}
                  draggable={!isRunning}
                  onDragStart={(e) => handleDragStart(e, block.id)}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDrop={(e) => handleDrop(e, index)}
                  onDragEnd={handleDragEnd}
                  className={`
                    relative group flex items-center gap-1 px-2 py-2 rounded border-2 transition-all
                    ${getBlockColor(block)}
                    ${isDragging ? 'opacity-50' : ''}
                    ${isDragOver ? 'border-yellow-400 scale-105' : 'border-transparent'}
                    ${!isRunning ? 'cursor-move hover:scale-105' : 'cursor-default'}
                  `}
                  style={{ minWidth: `${blockWidth}px` }}
                >
                  {!isRunning && (
                    <GripVertical size={12} className="text-white/50 group-hover:text-white" />
                  )}
                  <div className="flex items-center gap-1.5 flex-1">
                    {getBlockIcon(block)}
                    {block.type === 'motor' ? (
                      <select
                        value={block.action}
                        onChange={(e) => handleChangeAction(block.id, e.target.value)}
                        className="text-[10px] font-bold text-white bg-white/20 border border-white/30 rounded px-1 py-0.5 outline-none cursor-pointer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <option value="OPEN">OPEN</option>
                        <option value="CLOSE">CLOSE</option>
                        <option value="DIP">DIP</option>
                      </select>
                    ) : block.type === 'fan' || block.type === 'smoke' ? (
                      <select
                        value={block.action}
                        onChange={(e) => handleChangeAction(block.id, e.target.value)}
                        className="text-[10px] font-bold text-white bg-white/20 border border-white/30 rounded px-1 py-0.5 outline-none cursor-pointer"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <option value="start">Start</option>
                        <option value="stop">Stop</option>
                      </select>
                    ) : (
                      <span className="text-[10px] font-bold text-white whitespace-nowrap">
                        {getBlockLabel(block)}
                      </span>
                    )}
                    {block.type === 'fan' && block.action === 'start' && (
                      <span 
                        className="text-[9px] text-white/70 cursor-pointer hover:text-white"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleConfigClick(block);
                        }}
                        title="Click to edit fan speed"
                      >
                        {editingBlockId === block.id ? (
                          <input
                            type="number"
                            step="1"
                            min="0"
                            max="100"
                            value={editingConfig}
                            onChange={(e) => {
                              setEditingConfig(e.target.value);
                              handleConfigChange(block.id, e.target.value);
                            }}
                            onBlur={handleDurationBlur}
                            onKeyDown={(e) => handleDurationKeyDown(e, block.id)}
                            className="w-10 bg-white/20 text-white text-[9px] px-1 rounded border border-white/30 outline-none"
                            autoFocus
                          />
                        ) : (
                          `(${block.config?.fanSpeed || config.fanSpeed}%)`
                        )}
                      </span>
                    )}
                    {block.type === 'smoke' && block.action === 'start' && (
                      <span 
                        className="text-[9px] text-white/70 cursor-pointer hover:text-white"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleConfigClick(block);
                        }}
                        title="Click to edit smoke intensity"
                      >
                        {editingBlockId === block.id ? (
                          <input
                            type="number"
                            step="1"
                            min="0"
                            max="127"
                            value={editingConfig}
                            onChange={(e) => {
                              setEditingConfig(e.target.value);
                              handleConfigChange(block.id, e.target.value);
                            }}
                            onBlur={handleDurationBlur}
                            onKeyDown={(e) => handleDurationKeyDown(e, block.id)}
                            className="w-10 bg-white/20 text-white text-[9px] px-1 rounded border border-white/30 outline-none"
                            autoFocus
                          />
                        ) : (
                          `(${block.config?.smokeIntensity || config.smokeIntensity})`
                        )}
                      </span>
                    )}
                  </div>
                  <div 
                    className={`text-[9px] text-white/70 font-mono ${block.type === 'motor' ? 'cursor-default' : 'cursor-pointer hover:text-white'}`}
                    onClick={() => block.type !== 'motor' && handleDurationClick(block)}
                    title={block.type === 'motor' ? 'Duration calculated from motor movement' : 'Click to edit duration'}
                  >
                    {isEditing && block.type !== 'motor' ? (
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={editingDuration}
                        onChange={(e) => {
                          setEditingDuration(e.target.value);
                          handleDurationChange(block.id, e.target.value);
                        }}
                        onBlur={handleDurationBlur}
                        onKeyDown={(e) => handleDurationKeyDown(e, block.id)}
                        className="w-12 bg-white/20 text-white text-[9px] px-1 rounded border border-white/30 outline-none"
                        autoFocus
                      />
                    ) : (
                      `${duration.toFixed(1)}s`
                    )}
                  </div>
                  {!isRunning && (
                    <button
                      onClick={() => handleDeleteBlock(block.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-red-600 rounded"
                      title="Delete block"
                    >
                      <Trash2 size={10} className="text-white" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {timeline.length > 0 && (
        <div className="text-[9px] text-slate-500 text-center">
          Drag blocks to reorder • Click duration to edit • Hover to delete
        </div>
      )}
    </div>
  );
};

export default LoopTimeline;
