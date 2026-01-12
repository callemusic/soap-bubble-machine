
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
  dipWait: number;  // Seconds arms stay at DIP position after reaching it
  openWait: number;  // Seconds arms stay at OPEN position after reaching it
  blowDuration: number;  // Not used in automatic sequence (kept for backward compatibility)
  closeWait: number;  // Seconds arms stay at CLOSE position after reaching it
  fanSpeed: number;
  fanEnabled: boolean;
  fanStartDelay: number;  // Seconds delay after DIP phase ends before fan starts
  fanDuration: number;  // Total seconds fan should run (independent of arm movement timing)
  // Movement speed controls
  dipToOpenSpeed: number;  // Base step delay for DIP to OPEN movement (seconds)
  dipToOpenRampUp: number;  // Ramp-up steps for DIP to OPEN movement (acceleration at start)
  dipToOpenSlowIn: number;  // Slow-in steps for DIP to OPEN movement (deceleration at end)
  openToCloseSpeed: number;  // Base step delay for OPEN to CLOSE movement (seconds)
  openToCloseRampUp: number;  // Ramp-up steps for OPEN to CLOSE movement (acceleration at start)
  openToCloseSlowIn: number;  // Slow-in steps for OPEN to CLOSE movement (deceleration at end)
  closeToDipSpeed: number;  // Base step delay for CLOSE to DIP movement (seconds)
  closeToDipRampUp: number;  // Ramp-up steps for CLOSE to DIP movement (acceleration at start)
  closeToDipSlowIn: number;  // Slow-in steps for CLOSE to DIP movement (deceleration at end)
}

export const DEFAULT_CONFIG: SimulationConfig = {
  dipWait: 3.0,  // Seconds arms stay at DIP position after reaching it
  openWait: 2.0,  // Seconds arms stay at OPEN position after reaching it
  blowDuration: 5.0,  // Not used in automatic sequence (kept for backward compatibility)
  closeWait: 2.0,  // Seconds arms stay at CLOSE position after reaching it
  fanSpeed: 100,
  fanEnabled: true, // Fan is connected and enabled by default
  fanStartDelay: 1.6,  // Delay after DIP phase ends before fan starts
  fanDuration: 4.0,  // Total seconds fan should run (independent of arm movement)
  // Movement speed controls
  dipToOpenSpeed: 0.002,  // Base step delay for DIP to OPEN (seconds)
  dipToOpenRampUp: 0,  // Ramp-up steps for DIP to OPEN (acceleration at start)
  dipToOpenSlowIn: 150,  // Slow-in steps for DIP to OPEN (deceleration at end)
  openToCloseSpeed: 0.001,  // Base step delay for OPEN to CLOSE (seconds, faster)
  openToCloseRampUp: 0,  // Ramp-up steps for OPEN to CLOSE (acceleration at start)
  openToCloseSlowIn: 0,  // Slow-in steps for OPEN to CLOSE (deceleration at end)
  closeToDipSpeed: 0.002,  // Base step delay for CLOSE to DIP (seconds)
  closeToDipRampUp: 0,  // Ramp-up steps for CLOSE to DIP (acceleration at start)
  closeToDipSlowIn: 0,  // Slow-in steps for CLOSE to DIP (deceleration at end)
};