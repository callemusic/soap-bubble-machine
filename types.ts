
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
}

export const DEFAULT_CONFIG: SimulationConfig = {
  dipDuration: 5.0,
  liftDuration: 4.0,
  blowDuration: 3.0,
  closeDuration: 1.5,
  fanSpeed: 100,
  fanEnabled: true, // Default to enabled for 3-wire fan
  smokeEnabled: false,
  smokeIntensity: 120,
  smokeDuration: 3.0,
  smokeMidiChannel: 1,
  smokeMidiCC: 1,
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
};