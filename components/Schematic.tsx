
import React from 'react';
import { MachineState, SystemHighlight } from '../types';

interface SchematicProps {
  activeState: MachineState;
  fanSpeed: number;
  fanEnabled: boolean;
  fanRunning?: boolean;
  highlight?: SystemHighlight;
  motorAPosition?: number;
  motorBPosition?: number;
  movementDuration?: number;
}

const Schematic: React.FC<SchematicProps> = ({ activeState, fanSpeed, fanEnabled, fanRunning = false, highlight, motorAPosition = 0, motorBPosition = 0, movementDuration = 0 }) => {
  // Use actual fanRunning state from server, not just based on activeState
  const isFanOn = fanEnabled && fanRunning;
  const isSmokeOn = activeState === MachineState.BLOW || activeState === MachineState.CLOSE || activeState === MachineState.SMOKE_TEST;
  const isMotorMoving = activeState === MachineState.OPEN || activeState === MachineState.CLOSE || activeState === MachineState.DIP || activeState === MachineState.HOME;
  
  let armRotation = 0;
  // Use actual movement duration for 1:1 simulation, with minimum of 0.1s for smooth animation
  let transitionDuration = movementDuration > 0 ? `${Math.max(0.1, movementDuration)}s` : '1s';
  
  switch (activeState) {
    case MachineState.BLOW:
    case MachineState.SMOKE_TEST:
      armRotation = -75;
      transitionDuration = '1s';
      break;
    case MachineState.CLOSE:
      armRotation = 0;
      transitionDuration = movementDuration > 0 ? `${Math.max(0.1, movementDuration)}s` : '1.5s';
      break;
    case MachineState.IDLE:
       armRotation = -75; 
       transitionDuration = '1s';
       break;
    case MachineState.DIP:
      armRotation = 60;
      transitionDuration = movementDuration > 0 ? `${Math.max(0.1, movementDuration)}s` : '1s';
      break;
    case MachineState.OPEN:
    case MachineState.HOME:
      armRotation = -75;
      transitionDuration = movementDuration > 0 ? `${Math.max(0.1, movementDuration)}s` : '4s';
      break;
    default:
      armRotation = -75;
      break;
  }

  const getWireColor = (active: boolean, type: 'power' | 'signal' | 'ground' | 'data' | '12v' = 'signal') => {
    if (!active) return '#334155';
    if (type === 'power') return '#ef4444'; 
    if (type === '12v') return '#fbbf24'; 
    if (type === 'ground') return '#475569';
    if (type === 'data') return '#d946ef';
    return '#3b82f6';
  };

  const fanAnimDuration = isFanOn ? `${Math.max(0.1, 2.0 - (fanSpeed / 100) * 1.8)}s` : '0s';

  const getOpacity = (system: 'power' | 'motors' | 'logic') => {
    if (!highlight) return 1;
    return highlight === system ? 1 : 0.2;
  };

  return (
    <div className="w-full h-full bg-slate-900 rounded-xl border border-slate-700 overflow-hidden relative shadow-2xl">
      <div className="absolute top-4 left-4 z-10 bg-slate-800/80 backdrop-blur p-2 rounded text-xs text-slate-300 font-mono border border-slate-600">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full bg-red-500"></div> 24V Verified
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full bg-amber-400"></div> 12V Verified
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full bg-slate-600"></div> Common Ground
        </div>
      </div>

      <svg viewBox="0 0 1000 700" className="w-full h-full">
        {/* --- GROUND BUS --- */}
        <g style={{ opacity: highlight ? 0.3 : 1 }}>
          <path d="M 100 450 L 900 450" stroke="#475569" strokeWidth="4" fill="none" />
          <path d="M 110 120 L 110 450" stroke="#475569" strokeWidth="2" strokeDasharray="4 2" /> 
          <path d="M 230 180 L 230 450" stroke="#475569" strokeWidth="2" strokeDasharray="4 2" />
          <path d="M 630 180 L 630 450" stroke="#475569" strokeWidth="2" strokeDasharray="4 2" />
          <path d="M 855 125 L 855 450" stroke="#475569" strokeWidth="2" strokeDasharray="4 2" />
          <path d="M 885 125 L 885 450" stroke="#475569" strokeWidth="2" strokeDasharray="4 2" />
          <path d="M 230 530 L 230 450" stroke="#475569" strokeWidth="2" />
          <path d="M 460 290 L 460 450" stroke="#475569" strokeWidth="2" strokeDasharray="4 2" />
        </g>

        {/* --- POWER WIRES (RED 24V / YELLOW 12V) --- */}
        <g style={{ opacity: getOpacity('power'), transition: 'opacity 0.3s ease' }}>
          <path d="M 170 80 L 210 80 L 210 60" stroke={getWireColor(true, 'power')} strokeWidth="2" fill="none" /> 
          <path d="M 210 60 L 610 60" stroke={getWireColor(true, 'power')} strokeWidth="2" fill="none" />
          <path d="M 610 60 L 825 60 L 825 105" stroke={getWireColor(true, 'power')} strokeWidth="2" fill="none" />
          
          <path d="M 915 115 L 945 115 L 945 216 L 920 216" stroke={getWireColor(true, '12v')} strokeWidth="2" fill="none" />
          <path d="M 885 115 L 885 250 L 460 250" stroke="#475569" strokeWidth="2" fill="none" />
          <path d="M 460 250 L 460 290" stroke="#475569" strokeWidth="2" fill="none" />

          {/* PSU WITH AC LABELS */}
          <g transform="translate(50, 40)">
            <rect width="120" height="80" rx="4" fill="#1e293b" stroke={highlight === 'power' ? '#fbbf24' : '#10b981'} strokeWidth={highlight === 'power' ? 4 : 2} />
            <text x="60" y="35" textAnchor="middle" fill="#10b981" fontSize="14" fontWeight="bold">24V PSU</text>
            <text x="60" y="50" textAnchor="middle" fill="#10b981" fontSize="8" opacity="0.8">VERIFIED OK</text>
            <g fontSize="8" fill="#94a3b8" fontWeight="bold">
              <text x="10" y="70">L</text>
              <text x="25" y="70">N</text>
              <text x="40" y="70">⏚</text>
              <text x="80" y="70">V-</text>
              <text x="100" y="70">V+</text>
            </g>
          </g>
          
          <g transform="translate(810, 40)">
            <rect width="120" height="80" rx="4" fill="#0f172a" stroke={highlight === 'power' ? '#fbbf24' : '#10b981'} strokeWidth={highlight === 'power' ? 4 : 2} />
            <text x="60" y="30" textAnchor="middle" fill="#10b981" fontSize="10" fontWeight="bold">12V BUCK</text>
            <text x="60" y="45" textAnchor="middle" fill="#10b981" fontSize="8" opacity="0.8">VERIFIED OK</text>
          </g>
        </g>

        {/* MOTOR WIRES & DRIVERS */}
        <g style={{ opacity: getOpacity('motors'), transition: 'opacity 0.3s ease' }}>
          <g stroke={getWireColor(isMotorMoving)} strokeWidth="1" fill="none">
            <path d="M 340 140 L 360 140 L 360 350 L 170 350" />
            <path d="M 340 150 L 363 150 L 363 353 L 170 353" />
            <path d="M 340 160 L 366 160 L 366 347 L 170 347" />
            <path d="M 340 170 L 369 170 L 369 350 L 170 350" />
          </g>
          <g stroke={getWireColor(isMotorMoving)} strokeWidth="1" fill="none">
            <path d="M 740 140 L 760 140 L 760 350 L 830 350" />
            <path d="M 740 150 L 763 150 L 763 353 L 830 353" />
            <path d="M 740 160 L 766 160 L 766 347 L 830 347" />
            <path d="M 740 170 L 769 170 L 769 350 L 830 350" />
          </g>
          
          <g transform="translate(200, 40)">
            <rect width="150" height="140" rx="4" fill="#1e293b" stroke={highlight === 'motors' ? '#3b82f6' : (motorAPosition === 0 ? '#10b981' : '#475569')} strokeWidth={highlight === 'motors' ? 4 : (motorAPosition === 0 ? 3 : 2)} />
            <text x="75" y="25" textAnchor="middle" fill="#cbd5e1" fontSize="14" fontWeight="bold">TB6600 A</text>
            <text x="75" y="45" textAnchor="middle" fill={motorAPosition === 0 ? '#10b981' : '#60a5fa'} fontSize="11" fontFamily="monospace" fontWeight={motorAPosition === 0 ? 'bold' : 'normal'}>Pos: {motorAPosition}</text>
            {motorAPosition === 0 && <text x="75" y="60" textAnchor="middle" fill="#10b981" fontSize="9" fontFamily="monospace">● HOME</text>}
          </g>

          <g transform="translate(600, 40)">
            <rect width="150" height="140" rx="4" fill="#1e293b" stroke={highlight === 'motors' ? '#3b82f6' : (motorBPosition === 0 ? '#10b981' : '#475569')} strokeWidth={highlight === 'motors' ? 4 : (motorBPosition === 0 ? 3 : 2)} />
            <text x="75" y="25" textAnchor="middle" fill="#cbd5e1" fontSize="14" fontWeight="bold">TB6600 B</text>
            <text x="75" y="45" textAnchor="middle" fill={motorBPosition === 0 ? '#10b981' : '#60a5fa'} fontSize="11" fontFamily="monospace" fontWeight={motorBPosition === 0 ? 'bold' : 'normal'}>Pos: {motorBPosition}</text>
            {motorBPosition === 0 && <text x="75" y="60" textAnchor="middle" fill="#10b981" fontSize="9" fontFamily="monospace">● HOME</text>}
          </g>
        </g>

        {/* SIGNAL WIRES & LOGIC */}
        <g style={{ opacity: getOpacity('logic'), transition: 'opacity 0.3s ease' }}>
          <path d="M 70 530 L 70 200 L 190 200 L 190 120 L 210 120" stroke="#4ade80" strokeWidth="1.5" fill="none" />
          <path d="M 100 530 L 100 210 L 180 210 L 180 150 L 210 150" stroke="#facc15" strokeWidth="1.5" fill="none" />
          <path d="M 130 530 L 130 220 L 590 220 L 590 120 L 610 120" stroke="#22d3ee" strokeWidth="1.5" fill="none" />
          <path d="M 160 530 L 160 230 L 580 230 L 580 150 L 610 150" stroke="#fb923c" strokeWidth="1.5" fill="none" />
          <path d="M 190 530 L 190 230 L 460 230 L 460 250" stroke="#60a5fa" strokeWidth="1.5" fill="none" />
          
          <g transform="translate(40, 530)">
            <rect width="240" height="150" rx="6" fill="#064e3b" stroke={highlight === 'logic' ? '#10b981' : '#10b981'} strokeWidth={highlight === 'logic' ? 5 : 3} />
            <text x="120" y="80" textAnchor="middle" fill="#e2e8f0" fontSize="20" fontWeight="bold">Pi 3</text>
          </g>

          <g transform="translate(760, 580)">
            <rect width="120" height="60" rx="4" fill="#312e81" stroke={highlight === 'logic' ? '#818cf8' : '#818cf8'} strokeWidth={highlight === 'logic' ? 4 : 2} />
            <text x="60" y="25" textAnchor="middle" fill="#e2e8f0" fontSize="11" fontWeight="bold">DMX USB</text>
          </g>
        </g>

        {/* MECHANICAL ASSEMBLY */}
        <g transform="translate(100, 300)" style={{ opacity: highlight ? 0.4 : 1 }}>
           <rect width="70" height="70" rx="4" fill="#334155" stroke="#94a3b8" strokeWidth="2" />
           <g style={{ 
                transform: `rotate(${armRotation}deg)`, 
                transformOrigin: '35px 35px', 
                transition: `transform ${transitionDuration} ease-in-out` 
              }}>
              <rect x="35" y="30" width="240" height="10" rx="5" fill="#64748b" opacity="0.8" />
           </g>
        </g>

        <g transform="translate(830, 300)" style={{ opacity: highlight ? 0.4 : 1 }}>
           <rect width="70" height="70" rx="4" fill="#334155" stroke="#94a3b8" strokeWidth="2" />
           <g style={{ 
                transform: `rotate(${-armRotation + 180}deg)`, 
                transformOrigin: '35px 35px', 
                transition: `transform ${transitionDuration} ease-in-out` 
              }}>
              <rect x="35" y="30" width="240" height="10" rx="5" fill="#64748b" opacity="0.8" />
           </g>
        </g>

        <g transform="translate(460, 250)" style={{ opacity: highlight ? 0.4 : 1 }}>
             <circle cx="40" cy="40" r="40" fill={isFanOn ? "#1e3a8a" : "#334155"} stroke={!fanEnabled ? '#ef4444' : (isFanOn ? '#60a5fa' : '#64748b')} strokeWidth={isFanOn ? "3" : "2"} strokeDasharray={!fanEnabled ? "4 4" : "none"} />
             {fanEnabled ? (
               <g transform={isFanOn ? 'rotate(0 40 40)' : 'rotate(0 40 40)'}>
                 {isFanOn && <animateTransform attributeName="transform" type="rotate" from="0 40 40" to="360 40 40" dur={fanAnimDuration} repeatCount="indefinite" />}
                 <path d="M 40 40 L 40 10" stroke={isFanOn ? "#60a5fa" : "#cbd5e1"} strokeWidth="4" />
                 <path d="M 40 40 L 70 40" stroke={isFanOn ? "#60a5fa" : "#cbd5e1"} strokeWidth="4" />
                 {isFanOn && (
                   <text x="40" y="55" textAnchor="middle" fill="#60a5fa" fontSize="8" fontWeight="bold">ON</text>
                 )}
               </g>
             ) : (
               <g>
                 <text x="40" y="40" textAnchor="middle" fill="#ef4444" fontSize="10" fontWeight="bold">OFF</text>
               </g>
             )}
        </g>

        <g transform="translate(450, 350)" style={{ opacity: highlight ? 0.4 : 1 }}>
          <rect width="100" height="60" rx="4" fill="#3f3f46" stroke={isSmokeOn ? '#ef4444' : '#52525b'} strokeWidth="2" />
          <text x="50" y="30" textAnchor="middle" fill="#e4e4e7" fontSize="10" fontWeight="bold">SMOKE</text>
        </g>
      </svg>
    </div>
  );
};

export default Schematic;
