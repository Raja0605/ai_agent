import React, { useCallback, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  Info,
  Loader2,
  ShieldCheck,
  Trash2,
  Upload,
  XCircle,
} from 'lucide-react';
import type { AtsCheckResult, AtsIssue, ResumeProfile } from '../types/job';
import { checkAts } from '../services/aiService';
import { deleteResume, saveActiveResumeId, saveResumeText, uploadResumePdf } from '../services/resumeService';

/**
 * Resume vault: upload, inspect, ATS-check, delete.
 *
 * Two things this fixes beyond the UI. Deleting a resume used to be a no-op
 * that reported success. And resume text was parsed twice — once in the
 * browser with its own skill list and a flat "4 years of experience" for
 * everybody, and once on the server — so the skills shown to the user were
 * not the skills used for matching. Parsing now happens on the server only.
 */

interface ResumeVaultProps {
  resumes: ResumeProfile[];
  activeResume: ResumeProfile | null;
  onResumesChanged: () => Promise<void>;
  onActiveChanged: (resume: ResumeProfile) => void;
}

const SEVERITY_STYLE: Record<AtsIssue['severity'], { icon: React.ReactNode; classes: string }> = {
  critical: {
    icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
    classes: 'border-rose-500/30 bg-rose-500/5',
  },
  warning: {
    icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
    classes: 'border-amber-500/30 bg-amber-500/5',
  },
  info: {
    icon: <Info className="w-3.5 h-3.5 text-slate-400" />,
    classes: 'border-slate-700 bg-slate-950',
  },
};

export const ResumeVault: React.FC<ResumeVaultProps> = ({
  resumes,
  activeResume,
  onResumesChanged,
  onActiveChanged,
}) => {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pasteMode, setPasteMode] = useState(false);
  const [pastedText, setPastedText] = useState('');
  const [ats, setAts] = useState<{ resumeId: string; result: AtsCheckResult } | null>(null);
  const [checking, setChecking] = useState(false);

  const handleUpload = useCallback(
    async (file: File) => {
      setBusy(true);
      setError(null);
      try {
        const resume = await uploadResumePdf(file);
        await onResumesChanged();
        onActiveChanged(resume);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed.');
      } finally {
        setBusy(false);
      }
    },
    [onResumesChanged, onActiveChanged]
  );

  const handlePaste = async () => {
    if (!pastedText.trim()) return setError('Paste your resume text first.');
    setBusy(true);
    setError(null);
    try {
      const resume = await saveResumeText(pastedText, 'Pasted resume.txt');
      await onResumesChanged();
      onActiveChanged(resume);
      setPastedText('');
      setPasteMode(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save this resume.');
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (resume: ResumeProfile) => {
    setBusy(true);
    setError(null);
    try {
      await deleteResume(resume.id);
      if (ats?.resumeId === resume.id) setAts(null);
      await onResumesChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete this resume.');
    } finally {
      setBusy(false);
    }
  };

  const handleAtsCheck = async (resume: ResumeProfile) => {
    setChecking(true);
    setError(null);
    try {
      setAts({ resumeId: resume.id, result: await checkAts(resume) });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ATS check failed.');
    } finally {
      setChecking(false);
    }
  };

  const handleSetActive = (resume: ResumeProfile) => {
    saveActiveResumeId(resume.id);
    onActiveChanged(resume);
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
          <div>
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <FileText className="w-5 h-5 text-cyan-400" />
              Resume vault
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Jobs are scored against the active resume. Parsing happens on the server.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-bold shadow-lg shadow-cyan-500/20 cursor-pointer">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              Upload PDF
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                disabled={busy}
                onChange={e => {
                  const file = e.target.files?.[0];
                  if (file) void handleUpload(file);
                  e.target.value = '';
                }}
              />
            </label>
            <button
              onClick={() => setPasteMode(v => !v)}
              className="px-4 py-2.5 rounded-xl border border-slate-800 bg-slate-950 text-slate-300 hover:text-white text-xs font-semibold"
            >
              Paste text
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-start gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        {pasteMode && (
          <div className="space-y-3">
            <textarea
              value={pastedText}
              onChange={e => setPastedText(e.target.value)}
              rows={8}
              placeholder="Paste the full text of your resume here…"
              className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 font-mono focus:outline-none focus:border-cyan-500/50"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setPasteMode(false)}
                className="px-4 py-2 rounded-xl border border-slate-800 text-slate-400 hover:text-white text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handlePaste}
                disabled={busy}
                className="px-5 py-2 rounded-xl bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-xs font-bold disabled:opacity-50"
              >
                Save resume
              </button>
            </div>
          </div>
        )}

        {resumes.length === 0 ? (
          <div className="text-center py-12 space-y-3">
            <FileText className="w-10 h-10 text-slate-600 mx-auto" />
            <h3 className="text-sm font-bold text-slate-300">No resumes yet</h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Upload one to start scoring jobs. Until then, matching, tailoring and loop runs
              have nothing to compare against and will say so rather than guessing.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {resumes.map(resume => {
              const isActive = resume.id === activeResume?.id;
              return (
                <div
                  key={resume.id}
                  className={`p-5 rounded-2xl border space-y-4 transition-all ${
                    isActive
                      ? 'bg-slate-950/90 border-cyan-500/50 shadow-xl shadow-cyan-500/10'
                      : 'bg-slate-950/40 border-slate-800'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-bold text-slate-100 truncate">{resume.fileName}</h3>
                        {isActive && (
                          <span className="px-2 py-0.5 text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 rounded-full">
                            ACTIVE
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 truncate">
                        {resume.fullName} • {resume.targetRole}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {resume.experienceYears} yrs detected • uploaded {resume.uploadedAt}
                      </p>
                    </div>

                    <button
                      onClick={() => void handleDelete(resume)}
                      disabled={busy}
                      title="Delete this resume"
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-rose-400 shrink-0"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {resume.summary && (
                    <p className="text-xs text-slate-400 line-clamp-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
                      {resume.summary}
                    </p>
                  )}

                  <div className="space-y-1.5">
                    <span className="text-[10px] text-slate-500 font-semibold uppercase block">
                      Skills detected ({resume.skills.length})
                    </span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {resume.skills.length === 0 ? (
                        <span className="text-[11px] text-amber-400">
                          None detected — matching will be unreliable.
                        </span>
                      ) : (
                        resume.skills.map(skill => (
                          <span
                            key={skill}
                            className="text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300 font-mono"
                          >
                            {skill}
                          </span>
                        ))
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {!isActive && (
                      <button
                        onClick={() => handleSetActive(resume)}
                        className="flex-1 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
                      >
                        Make active
                      </button>
                    )}
                    <button
                      onClick={() => void handleAtsCheck(resume)}
                      disabled={checking}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl border border-slate-800 bg-slate-950 text-slate-300 hover:text-white text-xs font-semibold disabled:opacity-50"
                    >
                      {checking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                      ATS check
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ATS results */}
      {ats && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-cyan-400" />
                ATS parseability check
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Whether an applicant tracking system can actually read this document.
                Structural only — it does not judge your experience.
              </p>
            </div>
            <div className="text-right">
              <div
                className={`text-3xl font-extrabold ${
                  ats.result.score >= 80
                    ? 'text-emerald-400'
                    : ats.result.score >= 60
                      ? 'text-amber-400'
                      : 'text-rose-400'
                }`}
              >
                {ats.result.score}%
              </div>
              <span className="text-[11px] text-slate-500">{ats.result.wordCount} words extracted</span>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-slate-500 uppercase font-semibold">Sections found:</span>
            {ats.result.detectedSections.length === 0 ? (
              <span className="text-[11px] text-rose-400">None</span>
            ) : (
              ats.result.detectedSections.map(section => (
                <span
                  key={section}
                  className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 flex items-center gap-1"
                >
                  <CheckCircle2 className="w-3 h-3" />
                  {section}
                </span>
              ))
            )}
          </div>

          {ats.result.issues.length === 0 ? (
            <p className="text-xs text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              No structural problems found.
            </p>
          ) : (
            <div className="space-y-2">
              {ats.result.issues.map((issue, i) => {
                const style = SEVERITY_STYLE[issue.severity];
                return (
                  <div key={i} className={`p-3 rounded-xl border ${style.classes} space-y-1`}>
                    <div className="flex items-start gap-2">
                      <span className="mt-0.5 shrink-0">{style.icon}</span>
                      <span className="text-xs font-semibold text-slate-200">{issue.message}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 pl-6">{issue.fix}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
