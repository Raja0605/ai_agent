import React from 'react';
import { AlertTriangle, Bot, CheckCircle2, Cpu, Key, X } from 'lucide-react';
import type { AiRuntimeConfig } from '../types/job';

/**
 * Read-only report of the AI configuration in force.
 *
 * This replaces a settings modal with editable "Google Model", "OpenAI Model"
 * and "Vector Embeddings Model" text fields that were saved to localStorage
 * and then never used by anything: model selection and credentials live in
 * the server environment, so nothing typed here could ever have taken effect.
 * A control that does nothing is worse than no control, so it now reports the
 * truth and says where to change it.
 */

interface AiStatusModalProps {
  isOpen: boolean;
  config: AiRuntimeConfig | null;
  onClose: () => void;
}

export const AiStatusModal: React.FC<AiStatusModalProps> = ({ isOpen, config, onClose }) => {
  if (!isOpen) return null;

  const configured = config?.configured ?? false;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-lg overflow-hidden shadow-2xl">

        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center">
              {configured ? (
                <Bot className="w-5 h-5 text-indigo-400" />
              ) : (
                <Cpu className="w-5 h-5 text-slate-400" />
              )}
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">AI status</h2>
              <p className="text-xs text-slate-400">What the server is configured to use</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {!config ? (
            <p className="text-sm text-slate-500">Could not reach the backend to read its configuration.</p>
          ) : (
            <>
              <div
                className={`flex items-start gap-3 p-4 rounded-xl border ${
                  configured
                    ? 'bg-emerald-500/10 border-emerald-500/30'
                    : 'bg-amber-500/10 border-amber-500/30'
                }`}
              >
                {configured ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                )}
                <div className="space-y-1">
                  <p className={`text-sm font-bold ${configured ? 'text-emerald-300' : 'text-amber-300'}`}>
                    {configured ? 'AI evaluation active' : 'Running without AI'}
                  </p>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {configured
                      ? 'Opening a job runs a full model evaluation. Job lists and scheduled loop runs still use the deterministic scorer, because one model call per card would be slow and expensive.'
                      : 'No API key is set, so every score comes from keyword matching. Results are labelled accordingly throughout the app — nothing keyword-derived is presented as an AI judgement.'}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] font-semibold text-slate-500 uppercase block mb-1">Provider</span>
                  <span className="text-slate-200 font-mono">{config.providerName}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] font-semibold text-slate-500 uppercase block mb-1">Model</span>
                  <span className="text-slate-200 font-mono break-all">{config.model}</span>
                </div>
              </div>

              <div className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-950 border border-slate-800">
                <Key className="w-3.5 h-3.5 text-slate-500 mt-0.5 shrink-0" />
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Provider, model and credentials are all server-side settings. Change{' '}
                  <span className="font-mono text-slate-300">LLM_PROVIDER</span>,{' '}
                  <span className="font-mono text-slate-300">GEMINI_MODEL</span>/
                  <span className="font-mono text-slate-300">OPENAI_MODEL</span> and the matching{' '}
                  <span className="font-mono text-slate-300">*_API_KEY</span> in your{' '}
                  <span className="font-mono text-slate-300">.env</span>, then restart the backend.
                  Keys are never sent to the browser.
                </p>
              </div>
            </>
          )}
        </div>

        <div className="p-5 border-t border-slate-800 bg-slate-950/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
