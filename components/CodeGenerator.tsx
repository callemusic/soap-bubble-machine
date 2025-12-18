
import React, { useState } from 'react';
import { GoogleGenAI } from "@google/genai";
import { PinConfig, SimulationConfig } from '../types';
import { Bot, Copy, Check, Terminal, Loader2, Wifi, Zap, FileCode } from 'lucide-react';

interface CodeGeneratorProps {
  pins: PinConfig;
  config: SimulationConfig;
  piIp: string;
}

const CodeGenerator: React.FC<CodeGeneratorProps> = ({ pins, config, piIp }) => {
  const [code, setCode] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateCode = async () => {
    setLoading(true);
    setError(null);
    setCode('');
    
    // Check if API key is available
    const apiKey = process.env.API_KEY || process.env.GEMINI_API_KEY;
    if (!apiKey) {
      setError('Gemini API key not configured. The server.py file is already available in your project root. You can use that instead, or set GEMINI_API_KEY in a .env.local file.');
      setLoading(false);
      return;
    }
    
    try {
      const ai = new GoogleGenAI({ apiKey });
      
      const prompt = `
        You are an expert Python embedded systems engineer. Write a PRODUCTION-READY script for a Raspberry Pi 3.
        
        New Requirements for Phase 4:
        1. Include a '/health' GET route that returns {"status": "ok", "pi": "bubblebot"}.
        2. Ensure all GPIO actions (RPi.GPIO) are wrapped in try/except so the server doesn't crash if physical hardware is missing.
        3. Add a log message when commands are received.
        4. Enable CORS for all routes (important for web dashboard control).
        
        Context: The user is using Cursor IDE via Remote-SSH.
        Structure:
        - GLOBAL_CONFIG dictionary.
        - MotorController class.
        - Flask app with routes: /set_state, /update_config, /health.
        
        Hardware:
        - Motors: A(Step:${pins.stepA}, Dir:${pins.dirA}), B(Step:${pins.stepB}, Dir:${pins.dirB})
        - Fan: PWM ${pins.pwmFan} ${config.fanEnabled ? '(ENABLED)' : '(DISABLED - NOT CONNECTED)'}
        - DMX: Channel ${pins.dmxChannel}
        
        CRITICAL: The fan is currently ${config.fanEnabled ? 'ENABLED' : 'DISABLED'}.
        ${!config.fanEnabled ? 'Wrap ALL fan/PWM operations in try/except blocks. If fan is disabled, skip fan operations entirely and log "Fan disabled - skipping".' : 'Fan operations should be wrapped in try/except for safety.'}
        
        Default Timings:
        ${JSON.stringify(config, null, 2)}

        Provide ONLY the Python code in a block.
      `;

      const response = await ai.models.generateContent({
        model: 'gemini-3-pro-preview',
        contents: prompt,
      });

      const text = response.text || '';
      const match = text.match(/```python([\s\S]*?)```/);
      const cleanCode = match ? match[1].trim() : text;
      
      setCode(cleanCode);
    } catch (err: any) {
      setError(err.message || "Failed to generate code.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden flex flex-col h-full shadow-xl">
      <div className="p-4 bg-slate-800 border-b border-slate-700 flex justify-between items-center">
        <h3 className="font-bold text-slate-200 flex items-center gap-2 text-sm">
           <FileCode className="text-purple-400 w-4 h-4" />
           Firmware Deployment Center
        </h3>
        <button 
          onClick={generateCode} 
          disabled={loading}
          className="bg-purple-600 hover:bg-purple-500 text-white px-3 py-1.5 rounded text-xs font-bold transition-colors flex items-center gap-2"
        >
          {loading ? <Loader2 className="animate-spin w-3 h-3" /> : <Zap className="w-3 h-3" />}
          Build server.py
        </button>
      </div>

      {/* Terminal Snippets */}
      <div className="bg-black/40 p-3 border-b border-slate-800 space-y-2">
         <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Cursor Terminal Commands</div>
         <div className="grid grid-cols-1 gap-1">
            <div className="flex items-center justify-between bg-slate-950 p-1.5 rounded border border-slate-800 group">
               <code className="text-[10px] text-blue-400">pip install flask flask-cors RPi.GPIO</code>
               <button onClick={() => navigator.clipboard.writeText('pip install flask flask-cors RPi.GPIO')} className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-white transition-opacity"><Copy size={10}/></button>
            </div>
            <div className="flex items-center justify-between bg-slate-950 p-1.5 rounded border border-slate-800 group">
               <code className="text-[10px] text-green-400">python3 server.py</code>
               <button onClick={() => navigator.clipboard.writeText('python3 server.py')} className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-white transition-opacity"><Copy size={10}/></button>
            </div>
         </div>
      </div>

      <div className="flex-1 bg-slate-950 p-4 overflow-auto relative font-mono text-sm">
        {error && <div className="p-4 bg-red-900/30 border border-red-500/50 rounded text-red-200 text-xs">{error}</div>}
        
        {!code && !loading && (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-2 opacity-60 p-4">
            <Terminal size={32} />
            <p className="text-xs text-center">server.py is ready in your project root!</p>
            <p className="text-[10px] text-slate-600 text-center mt-2">Copy it to your Pi and run: python3 server.py</p>
            <p className="text-[10px] text-slate-600 text-center">Or use AI code generation (requires API key)</p>
          </div>
        )}

        {code && (
          <>
            <button onClick={handleCopy} className="absolute top-4 right-4 p-2 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 border border-slate-600 transition-colors">
              {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
            </button>
            <pre className="text-blue-300 text-[11px] leading-relaxed">
              <code>{code}</code>
            </pre>
          </>
        )}
      </div>
    </div>
  );
};

export default CodeGenerator;
