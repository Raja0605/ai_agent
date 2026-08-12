import React, { useState } from 'react';
import { 
  X, 
  Upload, 
  FileText, 
  CheckCircle2, 
  Trash2, 
  Plus, 
  Sparkles, 
  User, 
  Mail, 
  Briefcase, 
  Award,
  Check
} from 'lucide-react';
import type { ResumeProfile } from '../types/job';
import { parseResumeFromText, saveResume, deleteResume, saveActiveResumeId } from '../services/resumeService';

interface ResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  resumes: ResumeProfile[];
  activeResume: ResumeProfile;
  onUpdateResumes: (updatedResumes: ResumeProfile[], active: ResumeProfile) => void;
}

export const ResumeModal: React.FC<ResumeModalProps> = ({
  isOpen,
  onClose,
  resumes,
  activeResume,
  onUpdateResumes
}) => {
  const [activeTab, setActiveTab] = useState<'manage' | 'upload'>('manage');
  const [pasteText, setPasteText] = useState('');
  const [fileName, setFileName] = useState('');
  const [parsedPreview, setParsedPreview] = useState<ResumeProfile | null>(null);

  if (!isOpen) return null;

  const handleSelectActive = (id: string) => {
    saveActiveResumeId(id);
    const selected = resumes.find(r => r.id === id) || resumes[0];
    onUpdateResumes(resumes, selected);
  };

  const handleDelete = (id: string) => {
    if (resumes.length <= 1) {
      alert('You must keep at least one stored resume profile.');
      return;
    }
    const updated = deleteResume(id);
    const newActive = updated[0];
    onUpdateResumes(updated, newActive);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = (event.target?.result as string) || '';
      const parsed = parseResumeFromText(text || file.name, file.name);
      setParsedPreview(parsed);
    };
    reader.readAsText(file);
  };

  const handleParsePastedText = () => {
    if (!pasteText.trim()) return;
    const name = fileName.trim() || 'Custom_Uploaded_Resume.pdf';
    const parsed = parseResumeFromText(pasteText, name);
    setParsedPreview(parsed);
  };

  const handleSaveParsedResume = () => {
    if (!parsedPreview) return;
    const updatedList = saveResume(parsedPreview);
    onUpdateResumes(updatedList, parsedPreview);
    setParsedPreview(null);
    setPasteText('');
    setFileName('');
    setActiveTab('manage');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 p-[2px]">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <FileText className="w-5 h-5 text-cyan-400" />
              </div>
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">Resume Vault & Profile Manager</h2>
              <p className="text-xs text-slate-400">Store and select your resume for automated 1-click platform applications</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Subtabs */}
        <div className="flex items-center gap-2 px-6 pt-4 border-b border-slate-800/60 bg-slate-950/30">
          <button
            onClick={() => setActiveTab('manage')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'manage'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            Stored Resumes ({resumes.length})
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className={`pb-3 text-xs font-semibold border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'upload'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Plus className="w-4 h-4" />
            Upload New Resume
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          
          {activeTab === 'manage' && (
            <div className="space-y-4">
              <span className="text-xs text-slate-400 block">
                Select your default active resume profile below. When you click <strong className="text-cyan-400">Auto-Apply</strong>, this stored file will be uploaded automatically.
              </span>

              <div className="grid grid-cols-1 gap-4">
                {resumes.map(resume => {
                  const isActive = resume.id === activeResume.id;
                  return (
                    <div
                      key={resume.id}
                      className={`p-4 rounded-2xl border transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
                        isActive
                          ? 'bg-slate-950/90 border-cyan-500/50 shadow-lg shadow-cyan-500/10'
                          : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start gap-3.5">
                        <div className={`p-3 rounded-xl border ${
                          isActive ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' : 'bg-slate-900 border-slate-800 text-slate-400'
                        }`}>
                          <FileText className="w-6 h-6" />
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-bold text-slate-100">{resume.fileName}</h3>
                            {isActive && (
                              <span className="px-2 py-0.5 text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 rounded-full flex items-center gap-1">
                                <Check className="w-3 h-3 text-cyan-400" />
                                ACTIVE DEFAULT
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
                            <span className="flex items-center gap-1 text-slate-300 font-medium">
                              <User className="w-3.5 h-3.5 text-cyan-400" />
                              {resume.fullName}
                            </span>
                            <span className="flex items-center gap-1">
                              <Mail className="w-3.5 h-3.5 text-slate-500" />
                              {resume.email}
                            </span>
                            <span className="flex items-center gap-1 text-indigo-400">
                              <Briefcase className="w-3.5 h-3.5" />
                              {resume.targetRole}
                            </span>
                          </div>

                          {/* Skill Tags */}
                          <div className="flex items-center gap-1 flex-wrap pt-1">
                            {resume.skills.slice(0, 6).map(skill => (
                              <span key={skill} className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 font-mono">
                                {skill}
                              </span>
                            ))}
                            {resume.skills.length > 6 && (
                              <span className="text-[10px] text-slate-500">+{resume.skills.length - 6} more</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 self-end md:self-center">
                        {!isActive && (
                          <button
                            onClick={() => handleSelectActive(resume.id)}
                            className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-all"
                          >
                            Set Active
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(resume.id)}
                          className="p-2 rounded-xl border border-slate-800 hover:bg-rose-500/20 hover:border-rose-500/40 text-slate-400 hover:text-rose-300 transition-all"
                          title="Delete Resume"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === 'upload' && (
            <div className="space-y-6">
              {!parsedPreview ? (
                <>
                  {/* File Upload Drop Area */}
                  <div className="border-2 border-dashed border-slate-800 hover:border-cyan-500/50 rounded-2xl p-8 text-center bg-slate-950/40 hover:bg-slate-950/80 transition-all cursor-pointer relative group">
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt"
                      onChange={handleFileUpload}
                      className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                    />
                    <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mx-auto text-cyan-400 group-hover:scale-110 transition-transform">
                      <Upload className="w-6 h-6" />
                    </div>
                    <h3 className="text-sm font-bold text-slate-200 mt-3">Drag & Drop Resume File (.pdf, .docx, .txt)</h3>
                    <p className="text-xs text-slate-400 mt-1">Or click to browse from your device</p>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="h-[1px] bg-slate-800 flex-1" />
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Or Paste Resume Plain Text</span>
                    <div className="h-[1px] bg-slate-800 flex-1" />
                  </div>

                  {/* Manual Paste */}
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={fileName}
                      onChange={(e) => setFileName(e.target.value)}
                      placeholder="Resume File Title (e.g. DevOps_Senior_Architect_2026.pdf)"
                      className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    />
                    <textarea
                      rows={6}
                      value={pasteText}
                      onChange={(e) => setPasteText(e.target.value)}
                      placeholder="Paste your resume content, skill keywords (e.g., Docker, Kubernetes, Terraform, AWS, Python, CI/CD)..."
                      className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
                    />
                    <button
                      onClick={handleParsePastedText}
                      disabled={!pasteText.trim()}
                      className="flex items-center justify-center gap-2 w-full py-3 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-cyan-600/20"
                    >
                      <Sparkles className="w-4 h-4" />
                      Parse Resume Skills & Profile
                    </button>
                  </div>
                </>
              ) : (
                /* Parsed Resume Preview & Approval */
                <div className="bg-slate-950 border border-cyan-500/40 rounded-2xl p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      <h3 className="text-sm font-bold text-slate-100">Parsed Resume Profile Preview</h3>
                    </div>
                    <button
                      onClick={() => setParsedPreview(null)}
                      className="text-xs text-slate-400 hover:text-white"
                    >
                      Re-parse
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Candidate Name</span>
                      <span className="font-bold text-slate-200">{parsedPreview.fullName}</span>
                    </div>
                    <div className="bg-slate-900 p-3 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-500 uppercase block">Target Job Role</span>
                      <span className="font-bold text-indigo-400">{parsedPreview.targetRole}</span>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] font-semibold text-slate-400 block">Extracted Skill Set:</span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {parsedPreview.skills.map(skill => (
                        <span key={skill} className="px-2.5 py-1 rounded-lg bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-xs font-mono font-semibold">
                          ✓ {skill}
                        </span>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={handleSaveParsedResume}
                    className="flex items-center justify-center gap-2 w-full py-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-emerald-500/20 transition-all"
                  >
                    <Award className="w-4 h-4" />
                    Save to Resume Vault & Set as Active Default
                  </button>
                </div>
              )}
            </div>
          )}

        </div>

      </div>
    </div>
  );
};
