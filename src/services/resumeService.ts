import type { ResumeProfile } from '../types/job';

const RESUMES_STORAGE_KEY = 'job_pulse_user_resumes';
const ACTIVE_RESUME_KEY = 'job_pulse_active_resume_id';

export const DEFAULT_DEVOPS_RESUME: ResumeProfile = {
  id: 'resume-devops-default',
  fileName: 'DevOps_Senior_Architect_Resume.pdf',
  uploadedAt: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
  fileSize: '420 KB',
  fullName: 'Alex Vance',
  email: 'alex.vance.devops@example.com',
  phone: '+91 98765 43210',
  targetRole: 'DevOps Engineer / Cloud Infrastructure Lead',
  summary: 'Results-driven DevOps Specialist with 5+ years of experience engineering automated CI/CD pipelines, orchestrating Kubernetes (EKS/GKE) microservices, managing Infrastructure as Code (Terraform), and implementing cloud observability on AWS & Azure.',
  skills: [
    'Docker',
    'Kubernetes',
    'Terraform',
    'AWS',
    'CI/CD',
    'Jenkins',
    'GitHub Actions',
    'Python',
    'Prometheus',
    'Grafana',
    'Ansible',
    'Linux',
    'Shell Scripting',
    'Helm',
    'ArgoCD'
  ],
  experienceYears: 5,
  education: 'B.Tech in Computer Science & Engineering',
  rawText: `Alex Vance | DevOps Engineer | alex.vance.devops@example.com
Summary: 5+ years in Cloud Automation, Docker, Kubernetes, AWS EKS, Terraform IaC, Jenkins, GitHub Actions, Prometheus, Grafana, and Python script automation.`
};

export function getStoredResumes(): ResumeProfile[] {
  try {
    const saved = localStorage.getItem(RESUMES_STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch (err) {
    console.error('Error reading stored resumes:', err);
  }
  return [DEFAULT_DEVOPS_RESUME];
}

export function getActiveResume(): ResumeProfile {
  const resumes = getStoredResumes();
  const activeId = localStorage.getItem(ACTIVE_RESUME_KEY);
  const found = resumes.find(r => r.id === activeId);
  return found || resumes[0] || DEFAULT_DEVOPS_RESUME;
}

export function saveActiveResumeId(id: string): void {
  localStorage.setItem(ACTIVE_RESUME_KEY, id);
}

export function saveResume(profile: ResumeProfile): ResumeProfile[] {
  const current = getStoredResumes();
  const index = current.findIndex(r => r.id === profile.id);
  let updated: ResumeProfile[];
  if (index >= 0) {
    updated = [...current];
    updated[index] = profile;
  } else {
    updated = [profile, ...current];
  }
  localStorage.setItem(RESUMES_STORAGE_KEY, JSON.stringify(updated));
  saveActiveResumeId(profile.id);
  return updated;
}

export function deleteResume(id: string): ResumeProfile[] {
  const current = getStoredResumes();
  const updated = current.filter(r => r.id !== id);
  localStorage.setItem(RESUMES_STORAGE_KEY, JSON.stringify(updated));
  if (updated.length > 0) {
    saveActiveResumeId(updated[0].id);
  }
  return updated;
}

/**
 * Parse plain text resume to extract skills, name, role, email.
 */
export function parseResumeFromText(rawText: string, fileName: string): ResumeProfile {
  const knownSkillList = [
    'Docker', 'Kubernetes', 'Terraform', 'AWS', 'Azure', 'GCP', 'CI/CD',
    'Jenkins', 'GitHub Actions', 'Python', 'Prometheus', 'Grafana', 'Ansible',
    'Linux', 'Shell Scripting', 'Helm', 'ArgoCD', 'React', 'Node.js', 'Express',
    'TypeScript', 'JavaScript', 'MongoDB', 'SQL', 'Snowflake', 'PySpark', 'dbt',
    'Datadog', 'Go', 'Golang', 'Java', 'Vault', 'SonarQube', 'DevSecOps'
  ];

  const extractedSkills: string[] = [];
  const textLower = rawText.toLowerCase();

  knownSkillList.forEach(skill => {
    if (textLower.includes(skill.toLowerCase())) {
      extractedSkills.push(skill);
    }
  });

  // Extract email if present
  const emailMatch = rawText.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
  const email = emailMatch ? emailMatch[0] : 'candidate@example.com';

  // Extract phone if present
  const phoneMatch = rawText.match(/\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}/);
  const phone = phoneMatch ? phoneMatch[0] : '+91 98765 00000';

  const lines = rawText.split('\n').map(l => l.trim()).filter(Boolean);
  const fullName = lines[0] || 'Professional Candidate';
  const targetRole = lines[1] || 'DevOps & Software Engineer';

  return {
    id: 'resume-' + Date.now(),
    fileName,
    uploadedAt: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    fileSize: Math.round(rawText.length / 1024 + 10) + ' KB',
    fullName,
    email,
    phone,
    targetRole,
    summary: rawText.slice(0, 240) + '...',
    skills: extractedSkills.length > 0 ? extractedSkills : ['Docker', 'Kubernetes', 'AWS', 'Linux'],
    experienceYears: 4,
    education: 'Bachelor of Technology',
    rawText
  };
}
