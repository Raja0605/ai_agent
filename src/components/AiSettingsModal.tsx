import React, { useState } from 'react';
import { X, Bot, Key, Check, Cpu, Sparkles } from 'lucide-react';
import type { AiConfigState } from '../types/job';
import { saveAiConfig } from '../config/aiConfig';

interface AiSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: AiConfigState;
  onSave: (newConfig: AiConfigState) => void;
}

export const AiSettingsModal: React.FC<AiSettingsModalProps> = ({
  isOpen,
  onClose,
  config,
  onSave
}) => {
  const [form, setForm] = useState<AiConfigState>(config);
  const [savedSuccess, setSavedSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    saveAiConfig(form);
    onSave(form);
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-lg overflow-hidden shadow-2xl space-y-0">
        
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 p-[2px]">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Bot className="w-5 h-5 text-indigo-400" />
              </div>
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">AI Model & API Config</h2>
              <p className="text-xs text-slate-400">Configure Google Gemini & OpenAI credentials for ATS parsing</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">
          
          {/* Active Provider Selector */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              Primary AI Provider
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setForm(p => ({ ...p, activeProvider: 'google' }))}
                className={`p-3 rounded-xl border text-left transition-all ${
                  form.activeProvider === 'google'
                    ? 'bg-indigo-500/20 border-indigo-500 text-indigo-300 font-bold shadow-md shadow-indigo-500/10'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs">Google AI</span>
                  {form.activeProvider === 'google' && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                </div>
                <span className="text-[10px] text-slate-400 block mt-1 font-mono">{form.googleModel}</span>
              </button>

              <button
                type="button"
                onClick={() => setForm(p => ({ ...p, activeProvider: 'openai' }))}
                className={`p-3 rounded-xl border text-left transition-all ${
                  form.activeProvider === 'openai'
                    ? 'bg-purple-500/20 border-purple-500 text-purple-300 font-bold shadow-md shadow-purple-500/10'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs">OpenAI</span>
                  {form.activeProvider === 'openai' && <Check className="w-3.5 h-3.5 text-purple-400" />}
                </div>
                <span className="text-[10px] text-slate-400 block mt-1 font-mono">{form.openaiModel}</span>
              </button>
            </div>
          </div>

          {/* Google API Key Input */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-cyan-400" />
                Google API Key (Gemini)
              </span>
              <span className="text-[10px] text-emerald-400 font-mono">Configured</span>
            </label>
            <input
              type="password"
              value={form.googleApiKey}
              onChange={(e) => setForm(p => ({ ...p, googleApiKey: e.target.value }))}
              placeholder="AIzaSy..."
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* OpenAI API Key Input */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-purple-400" />
                OpenAI API Key
              </span>
              <span className="text-[10px] text-emerald-400 font-mono">Configured</span>
            </label>
            <input
              type="password"
              value={form.openaiApiKey}
              onChange={(e) => setForm(p => ({ ...p, openaiApiKey: e.target.value }))}
              placeholder="sk-proj-..."
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 font-mono focus:outline-none focus:border-purple-500"
            />
          </div>

          {/* Model Selection Specifiers */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="space-y-1">
              <label className="text-[10px] font-semibold text-slate-400 uppercase">Google Model</label>
              <input
                type="text"
                value={form.googleModel}
                onChange={(e) => setForm(p => ({ ...p, googleModel: e.target.value }))}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 font-mono text-xs"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-semibold text-slate-400 uppercase">OpenAI Model</label>
              <input
                type="text"
                value={form.openaiModel}
                onChange={(e) => setForm(p => ({ ...p, openaiModel: e.target.value }))}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 font-mono text-xs"
              />
            </div>
          </div>

          {/* Embeddings Model */}
          <div className="space-y-1 text-xs">
            <label className="text-[10px] font-semibold text-slate-400 uppercase">Vector Embeddings Model</label>
            <input
              type="text"
              value={form.embeddingsModel}
              onChange={(e) => setForm(p => ({ ...p, embeddingsModel: e.target.value }))}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 font-mono text-xs"
            />
          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-5 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white text-xs font-semibold"
          >
            Cancel
          </button>

          <button
            onClick={handleSave}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white text-xs font-bold shadow-md shadow-indigo-500/20"
          >
            {savedSuccess ? <Check className="w-4 h-4 text-emerald-300" /> : <Sparkles className="w-4 h-4" />}
            {savedSuccess ? 'Settings Saved!' : 'Save Configuration'}
          </button>
        </div>

      </div>
    </div>
  );
};
