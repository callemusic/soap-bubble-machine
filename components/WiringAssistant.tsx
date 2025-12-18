
import React, { useState } from 'react';
import { GoogleGenAI } from "@google/genai";
import { SystemHighlight } from '../types';
import { Zap, ShieldCheck, Loader2, Info, ChevronRight, X, Link, Laptop } from 'lucide-react';

interface WiringAssistantProps {
  onHighlight: (system: SystemHighlight) => void;
}

const WiringAssistant: React.FC<WiringAssistantProps> = ({ onHighlight }) => {
  const [loading, setLoading] = useState(false);
  const [guide, setGuide] = useState<string | null>(null);
  const [activeTopic, setActiveTopic] = useState<string | null>(null);

  const getWiringGuide = async (topic: string, highlight: SystemHighlight) => {
    setLoading(true);
    setActiveTopic(topic);
    onHighlight(highlight);
    setGuide(null);

    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      const prompt = `
        As a senior electronics engineer, provide a safe, step-by-step guide for: "${topic}".
        
        Context: 
        1. The user has a Pi 3 and is ready to connect it to their laptop for the first time.
        2. They want to deploy a Python Flask server.
        3. Explain:
           - How to find the Pi's IP address on the network.
           - How to SSH into the Pi (ssh pi@<ip>).
           - How to use the "Remote-SSH" extension in VS Code/Cursor.
           - Basic sanity checks (ping, terminal access).
        
        CRITICAL: Remind them that the Pi 3 only supports 2.4GHz WiFi (if connecting wirelessly).

        Format: Use markdown with clear bold steps.
      `;

      const response = await ai.models.generateContent({
        model: 'gemini-3-pro-preview',
        contents: prompt,
      });

      setGuide(response.text || "Could not generate guide.");
    } catch (err) {
      setGuide("Error generating instructions. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  const closeGuide = () => {
    setGuide(null);
    setActiveTopic(null);
    onHighlight(null);
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-xl flex flex-col h-full">
      <div className="p-4 bg-slate-800 border-b border-slate-700 flex justify-between items-center">
        <h3 className="font-bold text-slate-200 flex items-center gap-2">
          <Zap className="text-yellow-400 w-4 h-4" />
          Wiring & Logic Assistant
        </h3>
        {guide && (
          <button onClick={closeGuide} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        )}
      </div>

      <div className="flex-1 p-4 overflow-y-auto custom-scrollbar">
        {!guide && !loading ? (
          <div className="space-y-3">
            <p className="text-xs text-slate-400 mb-4">Select a system to see detailed connection instructions and safety steps.</p>
            
            <button 
              onClick={() => getWiringGuide("Initial Pi Setup & Laptop Link (SSH)", "logic")}
              className="w-full flex items-center justify-between p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg transition-all group animate-pulse-slow"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-900/30 rounded text-blue-400"><Laptop size={16} /></div>
                <div className="text-left">
                  <div className="text-sm font-medium text-blue-100">Link Laptop to Pi</div>
                  <div className="text-[10px] text-blue-400 uppercase font-bold">CURRENT STEP: SSH & IP Setup</div>
                </div>
              </div>
              <ChevronRight size={14} className="text-blue-400 group-hover:text-blue-300" />
            </button>

            <button 
              onClick={() => getWiringGuide("Common Grounding & Signal Integrity", "logic")}
              className="w-full flex items-center justify-between p-3 bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-lg transition-all group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-900/30 rounded text-indigo-400"><Link size={16} /></div>
                <div className="text-left">
                  <div className="text-sm font-medium text-slate-200">Common Grounding Strategy</div>
                  <div className="text-[10px] text-slate-500 uppercase">Hardware Prerequisite</div>
                </div>
              </div>
              <ChevronRight size={14} className="text-slate-600 group-hover:text-slate-400" />
            </button>

            <button 
              onClick={() => getWiringGuide("Main 24V Power Distribution", "power")}
              className="w-full flex items-center justify-between p-3 bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-lg transition-all group"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-900/30 rounded text-red-400"><Zap size={16} /></div>
                <div className="text-left">
                  <div className="text-sm font-medium text-slate-200">Finalizing 24V Bus</div>
                  <div className="text-[10px] text-slate-500 uppercase">PSU → Drivers → Buck</div>
                </div>
              </div>
              <ChevronRight size={14} className="text-slate-600 group-hover:text-slate-400" />
            </button>
          </div>
        ) : loading ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-4">
            <Loader2 className="animate-spin w-8 h-8 text-yellow-500" />
            <div className="text-center">
              <p className="text-sm font-medium text-slate-300">Generating safety guide...</p>
              <p className="text-xs">Analyzing {activeTopic}</p>
            </div>
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none text-slate-300">
            <div className="flex items-center gap-2 mb-4 p-2 bg-yellow-900/20 border border-yellow-500/30 rounded text-yellow-200 text-xs">
              <ShieldCheck size={14} className="flex-none" />
              <span>Instructions are AI-generated. Use with caution.</span>
            </div>
            <div className="whitespace-pre-wrap leading-relaxed text-xs">
              {guide}
            </div>
          </div>
        )}
      </div>

      {!guide && !loading && (
        <div className="p-3 bg-slate-950/50 flex items-center gap-2 text-[10px] text-slate-500 border-t border-slate-800">
          <Info size={12} />
          <span>Instructions are AI-generated. Use with caution.</span>
        </div>
      )}
    </div>
  );
};

export default WiringAssistant;
