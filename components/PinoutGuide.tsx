
import React from 'react';
import { PinConfig, SystemHighlight } from '../types';
import { Tablet, List, ArrowRight, Info, Zap, Activity, CheckCircle2, AlertOctagon, ShieldCheck, Link, Terminal, Wifi, Code } from 'lucide-react';

interface PinoutGuideProps {
  pins: PinConfig;
  onHighlight: (system: SystemHighlight) => void;
}

const PinoutGuide: React.FC<PinoutGuideProps> = ({ pins, onHighlight }) => {
  const connections = [
    { name: 'Motor A Step', bcm: pins.stepA, phys: 11, term: 'PUL+', highlight: 'motors' as SystemHighlight },
    { name: 'Motor A Dir', bcm: pins.dirA, phys: 13, term: 'DIR+', highlight: 'motors' as SystemHighlight },
    { name: 'Motor B Step', bcm: pins.stepB, phys: 15, term: 'PUL+', highlight: 'motors' as SystemHighlight },
    { name: 'Motor B Dir', bcm: pins.dirB, phys: 16, term: 'DIR+', highlight: 'motors' as SystemHighlight },
    { name: 'Fan (MOSFET)', bcm: pins.pwmFan, phys: 12, term: 'SIG / PWM', highlight: 'logic' as SystemHighlight },
    { name: 'Ground', bcm: 'GND', phys: 6, term: 'Common Ground', highlight: 'power' as SystemHighlight },
  ];

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-xl flex flex-col h-full">
      <div className="p-4 bg-slate-800 border-b border-slate-700 flex justify-between items-center">
        <h3 className="font-bold text-slate-200 flex items-center gap-2">
          <Tablet className="text-blue-400 w-4 h-4" />
          Hardware Connection Guide
        </h3>
        <div className="flex items-center gap-1 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded text-[10px] text-emerald-400 font-bold uppercase tracking-wider">
           <ShieldCheck size={10} /> Power Verified
        </div>
      </div>

      <div className="flex-1 p-4 overflow-y-auto custom-scrollbar space-y-6">
        
        {/* SOFTWARE SETUP CHECKLIST */}
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 text-slate-400 font-bold text-[10px] uppercase tracking-widest">
            <Code size={14} className="text-purple-500" /> Software Checklist
          </div>
          <div className="space-y-2">
             <div className="flex items-center justify-between p-2 bg-slate-900 rounded border border-slate-800">
                <div className="flex items-center gap-2">
                   <Wifi size={12} className="text-slate-500" />
                   <span className="text-[10px] text-slate-300">Pi on Network</span>
                </div>
                <div className="w-3 h-3 rounded-full border border-slate-700"></div>
             </div>
             <div className="flex items-center justify-between p-2 bg-slate-900 rounded border border-slate-800">
                <div className="flex items-center gap-2">
                   <Terminal size={12} className="text-slate-500" />
                   <span className="text-[10px] text-slate-300">SSH Enabled</span>
                </div>
                <div className="w-3 h-3 rounded-full border border-slate-700"></div>
             </div>
             <div className="flex items-center justify-between p-2 bg-slate-900 rounded border border-slate-800">
                <div className="flex items-center gap-2">
                   <Link size={12} className="text-slate-500" />
                   <span className="text-[10px] text-slate-300">Flask Server Run</span>
                </div>
                <div className="w-3 h-3 rounded-full border border-slate-700"></div>
             </div>
          </div>
        </div>

        {/* COMMON GROUND ALERT */}
        <div className="bg-indigo-950/30 border border-indigo-500/50 rounded-xl p-4 space-y-3">
           <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-widest">
              <Link size={14} /> Critical: Common Ground
           </div>
           <p className="text-[11px] text-indigo-100/80 leading-relaxed">
             Pi Pin 6 (GND) must go to PSU V- before connecting signal pins.
           </p>
        </div>

        {/* FAN WIRING INSTRUCTIONS */}
        <div className="bg-blue-950/30 border border-blue-500/50 rounded-xl p-4 space-y-3">
           <div className="flex items-center gap-2 text-blue-400 font-bold text-xs uppercase tracking-widest">
              <Zap size={14} /> Fan Wiring (2-Wire DC Fan)
           </div>
           <div className="space-y-2 text-[11px] text-blue-100/90 leading-relaxed">
             <div className="flex items-start gap-2">
               <span className="font-bold text-blue-300">1.</span>
               <span><strong className="text-yellow-300">Fan Positive (Red wire)</strong> → Connect to <strong>12V output</strong> from your 12V Buck Converter</span>
             </div>
             <div className="flex items-start gap-2">
               <span className="font-bold text-blue-300">2.</span>
               <span><strong className="text-yellow-300">Fan Negative (Black wire)</strong> → Connect to <strong>MOSFET Drain (D)</strong> terminal</span>
             </div>
             <div className="flex items-start gap-2">
               <span className="font-bold text-blue-300">3.</span>
               <span><strong className="text-yellow-300">MOSFET Source (S)</strong> → Connect to <strong>Common Ground</strong> (PSU V-)</span>
             </div>
             <div className="flex items-start gap-2">
               <span className="font-bold text-blue-300">4.</span>
               <span><strong className="text-yellow-300">MOSFET Gate (G)</strong> → Connect to <strong>Pi GPIO Pin 18</strong> (Physical Pin 12, BCM 18)</span>
             </div>
             <div className="mt-2 pt-2 border-t border-blue-500/30 text-[10px] text-blue-200/70 italic">
               ⚠️ Most DC fans run on 12V. Check your fan's voltage rating before connecting!
             </div>
           </div>
        </div>

        {/* GPIO Mapping Table */}
        <div className="space-y-2 pt-4 border-t border-slate-800">
           <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
              <List size={14} /> GPIO Connection Map
           </h4>
           <div className="space-y-1">
              {connections.map((conn, idx) => (
                <div 
                  key={idx}
                  onMouseEnter={() => onHighlight(conn.highlight)}
                  onMouseLeave={() => onHighlight(null)}
                  className="group flex items-center justify-between p-2 rounded-lg bg-slate-800/50 border border-slate-800 hover:border-blue-500/50 transition-all cursor-help"
                >
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-slate-200">{conn.name}</span>
                    <span className="text-[10px] text-slate-500 font-mono">BCM {conn.bcm}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col items-center">
                      <span className="text-[10px] text-slate-500 uppercase">Pin #</span>
                      <span className="text-xs font-bold text-blue-400">{conn.phys}</span>
                    </div>
                    <ArrowRight size={12} className="text-slate-600" />
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] text-slate-500 uppercase">Terminal</span>
                      <span className="text-xs font-bold text-slate-300">{conn.term}</span>
                    </div>
                  </div>
                </div>
              ))}
           </div>
        </div>

      </div>
    </div>
  );
};

export default PinoutGuide;
