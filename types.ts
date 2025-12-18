
export enum MachineState {
  IDLE = 'IDLE',
  DIP = 'DIP',
  OPEN = 'OPEN',
  BLOW = 'BLOW',
  CLOSE = 'CLOSE',
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
}

export const DEFAULT_CONFIG: SimulationConfig = {
  dipDuration: 5.0,
  liftDuration: 4.0,
  blowDuration: 3.0,
  closeDuration: 1.5,
  fanSpeed: 100,
  fanEnabled: false, // Default to disabled for testing without fan
};