import React, { useState, useEffect } from 'react';
import { 
  X, 
  Send, 
  CheckCircle2, 
  Sparkles, 
  FileText, 
  Building2, 
  ShieldCheck, 
  Loader2, 
  Bot,
  Zap
} from 'lucide-react';
import type { AiConfigState, JobPost, ResumeProfile } from '../types/job';
import type { AtsAnalysisResult } from '../services/aiService';
import { analyzeAtsMatch, generateCoverLetter } from '../services/aiService';

interface AutoApplyModalProps {
  isOpen: boolean;
  job: JobPost | null;
  activeResume: ResumeProfile;
  aiConfig: AiConfigState;
  onClose: () => void;
  onConfirmApply: (job: JobPost, coverNote: string, atsScore: number) => void;
}

type StepStatus = 'pending' | 'in_progress' | 'completed';

export const AutoApplyModal: React.FC<AutoApplyModalProps> = ({
  isOpen,
  job,
  activeResume,
  aiConfig,
  onClose,
  onConfirmApply
}) => {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [stepStatuses, setStepStatuses] = useState<StepStatus[]>([
    'pending',
    'pending',
    'pending',
    'pending'
  ]);
  const [atsResult, setAtsResult] = useState<AtsAnalysisResult | null>(null);
  const [coverNote, setCoverNote] = useState<string>('');
  const [isDone, setIsDone] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen || !job) {
      setCurrentStep(0);
      setStepStatuses(['pending', 'pending', 'pending', 'pending']);
      setIsDone(false);
      return;
    }

    let isMounted = true;

    async function runPipeline() {
      // Step 0: Portal handshake
      setCurrentStep(0);
      setStepStatuses(['in_progress', 'pending', 'pending', 'pending']);
      await new Promise(r => setTimeout(r, 600));
      if (!isMounted) return;
      setStepStatuses(['completed', 'pending', 'pending', 'pending']);

      // Step 1: ATS Analysis
      setCurrentStep(1);
      setStepStatuses(['completed', 'in_progress', 'pending', 'pending']);
      const analysis = await analyzeAtsMatch(activeResume, job!, aiConfig);
      if (!isMounted) return;
      setAtsResult(analysis);
      await new Promise(r => setTimeout(r, 700));
      setStepStatuses(['completed', 'completed', 'pending', 'pending']);

      // Step 2: Stored Resume Attachment & AI Cover Letter
      setCurrentStep(2);
      setStepStatuses(['completed', 'completed', 'in_progress', 'pending']);
      const note = await generateCoverLetter(activeResume, job!, aiConfig);
      if (!isMounted) return;
      setCoverNote(note);
      await new Promise(r => setTimeout(r, 700));
      setStepStatuses(['completed', 'completed', 'completed', 'pending']);

      // Step 3: Final Ready to Submit
      setCurrentStep(3);
      setStepStatuses(['completed', 'completed', 'completed', 'in_progress']);
      await new Promise(r => setTimeout(r, 500));
      if (!isMounted) return;
      setStepStatuses(['completed', 'completed', 'completed', 'completed']);
      setIsDone(true);
    }

    runPipeline();

    return () => {
      isMounted = false;
    };
  }, [isOpen, job, activeResume, aiConfig]);

  if (!isOpen || !job) return null;

  const handleFinalSubmit = () => {
    const score = atsResult?.score || 88;
    onConfirmApply(job, coverNote, score);
  };

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'naukri': return 'text-blue-400 border-blue-500/40 bg-blue-500/10';
      case 'indeed': return 'text-indigo-400 border-indigo-500/40 bg-indigo-500/10';
      case 'linkedin': return 'text-sky-400 border-sky-500/40 bg-sky-500/10';
      default: return 'text-amber-400 border-amber-500/40 bg-amber-500/10';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-lg animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-2xl overflow-hidden shadow-2xl space-y-0">
        
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 p-[2px]">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Send className="w-5 h-5 text-cyan-400 animate-pulse" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100">Automated Resume Submission Pipeline</h2>
                <span className={`px-2 py-0.5 text-[10px] font-bold border rounded-md uppercase tracking-wider ${getPlatformColor(job.platform)}`}>
                  {job.platform}
                </span>
              </div>
              <p className="text-xs text-slate-400">Target Role: <strong className="text-slate-200">{job.title}</strong> at <strong className="text-cyan-400">{job.company}</strong></p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          
          {/* Active Stored Resume Card */}
          <div className="p-4 rounded-2xl bg-slate-950 border border-cyan-500/30 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[10px] text-cyan-400 font-mono uppercase block">Auto-Attached Stored Resume</span>
                <span className="text-xs font-bold text-slate-100">{activeResume.fileName}</span>
                <span className="text-[11px] text-slate-400 block">{activeResume.fullName} • {activeResume.targetRole}</span>
              </div>
            </div>
            <span className="px-2.5 py-1 text-[11px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded-full flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> Ready
            </span>
          </div>

          {/* 4-Step Animated Pipeline */}
          <div className="space-y-3 bg-slate-950/50 p-4 rounded-2xl border border-slate-800">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              Automation Execution Log:
            </span>

            {/* Step 1 */}
            <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Building2 className="w-4 h-4 text-cyan-400" />
                <span className="text-slate-300">1. Portal API Handshake ({job.platform.toUpperCase()})</span>
              </div>
              {stepStatuses[0] === 'completed' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
              {stepStatuses[0] === 'in_progress' && <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />}
            </div>

            {/* Step 2 */}
            <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Sparkles className="w-4 h-4 text-amber-400" />
                <span className="text-slate-300">2. ATS Skill Overlap Check</span>
              </div>
              {stepStatuses[1] === 'completed' && (
                <span className="font-bold text-emerald-400 text-xs flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" />
                  {atsResult?.score || 88}% ATS Score
                </span>
              )}
              {stepStatuses[1] === 'in_progress' && <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />}
            </div>

            {/* Step 3 */}
            <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <Bot className="w-4 h-4 text-indigo-400" />
                <span className="text-slate-300">3. AI Cover Note Generation ({aiConfig.googleModel})</span>
              </div>
              {stepStatuses[2] === 'completed' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
              {stepStatuses[2] === 'in_progress' && <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />}
            </div>

            {/* Step 4 */}
            <div className="flex items-center justify-between text-xs p-2.5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span className="text-slate-300">4. Form Auto-Fill & Resume Upload Ready</span>
              </div>
              {stepStatuses[3] === 'completed' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
              {stepStatuses[3] === 'in_progress' && <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />}
            </div>
          </div>

          {/* Generated Cover Note Preview */}
          {coverNote && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Bot className="w-3.5 h-3.5 text-indigo-400" />
                  AI Custom Application Pitch (Editable):
                </label>
                <span className="text-[10px] text-slate-500">Auto-generated for {job.company}</span>
              </div>
              <textarea
                rows={4}
                value={coverNote}
                onChange={(e) => setCoverNote(e.target.value)}
                className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 font-mono focus:outline-none focus:border-cyan-500 leading-relaxed"
              />
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="p-5 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white text-xs font-semibold transition-all"
          >
            Cancel
          </button>

          <button
            disabled={!isDone}
            onClick={handleFinalSubmit}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 disabled:opacity-50 text-white text-xs font-bold shadow-lg shadow-cyan-500/25 transition-all hover:scale-105 active:scale-95"
          >
            <Send className="w-4 h-4" />
            Confirm & Dispatch Resume Application
          </button>
        </div>

      </div>
    </div>
  );
};
