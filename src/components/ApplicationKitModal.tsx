import type { JobPost, ResumeProfile } from '../types/job';
interface Props { isOpen: boolean; job: JobPost | null; activeResume: ResumeProfile | null; isApplied: boolean; onClose: () => void; onTrackApplication: (job: JobPost, coverNote: string, matchScore: number | null) => Promise<void>; }
export function ApplicationKitModal({isOpen,job,isApplied,onClose,onTrackApplication}: Props) {
 if (!isOpen || !job) return null;
 const apply = async () => { await onTrackApplication(job, '', job.match?.score ?? null); if (job.applyUrl) window.open(job.applyUrl, '_blank', 'noopener,noreferrer'); };
 return <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4"><section className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-xl bg-white p-6"><div className="flex justify-between gap-4"><div><h2 className="text-xl font-bold">{job.title}</h2><p>{job.company} · {job.location}</p></div><button onClick={onClose}>Close</button></div><p className="mt-5 whitespace-pre-wrap text-sm text-gray-700">{job.description}</p><div className="mt-6 flex gap-3"><button onClick={()=>void apply()} className="rounded bg-blue-600 px-4 py-2 text-white">{isApplied?'Open listing':'Open listing and track'}</button><button onClick={onClose} className="rounded border px-4 py-2">Cancel</button></div></section></div>;
}
