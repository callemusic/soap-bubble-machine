
export enum MachineState {
  IDLE = 'IDLE',
  DIP = 'DIP',
  OPEN = 'OPEN',
  BLOW = 'BLOW',
  CLOSE = 'CLOSE',
  HOME = 'HOME',
  SMOKE_TEST = 'SMOKE_TEST'
}

// SystemHighlight type for technical documentation and wiring guidance
export type SystemHighlight = 'power' | 'motors' | 'logic' | null;

export interface PinConfig {
  stepA: number;
  dirA: number;
  stepB: number;
  dirB: number;
  pwmFan: number;
  dmxChannel: number;
}

export const DEFAULT_PINS: PinConfig = {
  stepA: 17,
  dirA: 27,
  stepB: 22,
  dirB: 23,
  pwmFan: 18,
  dmxChannel: 1,
};

export type TimelineBlockType = 'motor' | 'fan' | 'smoke';
export type TimelineTrackType = 'motors' | 'fan' | 'smoke';

export interface TimelineBlock {
  id: string;
  type: TimelineBlockType;
  // For motor: 'OPEN' | 'CLOSE' | 'DIP'
  // For fan: 'start' | 'stop'
  // For smoke: 'start' | 'stop'
  action: string;
  startTime: number; // seconds from loop start
  duration: number; // in seconds (0 for instant actions like motor movements, calculated dynamically)
  // Additional config for fan/smoke
  config?: {
    fanSpeed?: number;
    smokeIntensity?: number;
  };
}

export interface TimelineTrack {
  id: string;
  type: TimelineTrackType;
  name: string;
  blocks: TimelineBlock[];
}

export interface SimulationConfig {
  dipDuration: number;
  liftDuration: number;
  blowDuration: number;
  closeDuration: number;
  fanSpeed: number;
  fanEnabled: boolean;
  smokeEnabled: boolean;
  smokeIntensity: number;
  smokeDuration: number;
  smokeMidiChannel: number;
  smokeMidiCC: number;
  // Motor position targets for each state
  motorADipPosition: number;
  motorBDipPosition: number;
  motorAOpenPosition: number;
  motorBOpenPosition: number;
  motorAClosePosition: number;
  motorBClosePosition: number;
  // Wait times between loop states (in seconds)
  waitAfterOpen: number;  // Wait after reaching OPEN before starting CLOSE
  waitAfterClose: number; // Wait after reaching CLOSE before starting DIP
  waitAfterDip: number;   // Wait after reaching DIP before starting OPEN
  // Multi-track timeline-based loop configuration
  loopTimeline: TimelineTrack[];
  loopDuration: number; // Total duration of the loop in seconds
}

export const DEFAULT_CONFIG: SimulationConfig = {
  dipDuration: 5.0,
  liftDuration: 4.0,
  blowDuration: 3.0,
  closeDuration: 1.5,
  fanSpeed: 100,
  fanEnabled: true, // Default to enabled for 3-wire fan
  smokeEnabled: false,
  smokeIntensity: 127, // Full intensity for DOREMiDi MTD-10
  smokeDuration: 3.0,
  smokeMidiChannel: 0, // MIDI Channel 0 (0-based) = Channel 1 (1-based)
  smokeMidiCC: 1, // CC number 1
  // Default motor positions (will be set via calibration)
  motorADipPosition: 200,
  motorBDipPosition: -200,
  motorAOpenPosition: -400,
  motorBOpenPosition: 400,
  motorAClosePosition: 200,
  motorBClosePosition: -200,
  // Default wait times between loop states (in seconds)
  waitAfterOpen: 1.0,
  waitAfterClose: 1.0,
  waitAfterDip: 1.0,
  // Default multi-track timeline
  loopTimeline: [
    {
      id: 'track-motors',
      type: 'motors',
      name: 'Motors',
      blocks: [
        { id: 'm1', type: 'motor', action: 'OPEN', startTime: 0, duration: 0 },
        { id: 'm2', type: 'motor', action: 'CLOSE', startTime: 2, duration: 0 },
        { id: 'm3', type: 'motor', action: 'DIP', startTime: 4, duration: 0 },
      ],
    },
    {
      id: 'track-fan',
      type: 'fan',
      name: 'Fan',
      blocks: [
        { id: 'f1', type: 'fan', action: 'start', startTime: 6, duration: 3.0, config: { fanSpeed: 100 } },
        { id: 'f2', type: 'fan', action: 'stop', startTime: 9, duration: 0 },
      ],
    },
    {
      id: 'track-smoke',
      type: 'smoke',
      name: 'Smoke',
      blocks: [],
    },
  ],
  loopDuration: 10.0, // Default loop duration
};