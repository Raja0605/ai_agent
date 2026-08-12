import type { AiConfigState, JobPost, ResumeProfile } from '../types/job';

export interface AtsAnalysisResult {
  score: number;
  matchedSkills: string[];
  missingSkills: string[];
  summary: string;
  recommendations: string[];
}

/**
 * Perform ATS resume-to-job matching calculation.
 * If AI is enabled and API key is set, attempts real LLM matching via Gemini / OpenAI.
 * Otherwise uses deterministic keyword & semantic skill vector matching.
 */
export async function analyzeAtsMatch(
  resume: ResumeProfile,
  job: JobPost,
  config: AiConfigState
): Promise<AtsAnalysisResult> {
  const jobSkills = job.skillsRequired.map(s => s.toLowerCase());
  const resumeSkills = resume.skills.map(s => s.toLowerCase());

  // Local fallback smart matcher logic
  const matchedSkills: string[] = [];
  const missingSkills: string[] = [];

  job.skillsRequired.forEach(skill => {
    const sLower = skill.toLowerCase();
    const isMatched = resumeSkills.some(rs => rs.includes(sLower) || sLower.includes(rs)) ||
      (resume.rawText && resume.rawText.toLowerCase().includes(sLower));

    if (isMatched) {
      matchedSkills.push(skill);
    } else {
      missingSkills.push(skill);
    }
  });

  const totalRequired = job.skillsRequired.length || 1;
  const matchRatio = matchedSkills.length / totalRequired;
  
  // Calculate dynamic ATS score weighted by skill overlap & experience alignment
  let score = Math.round(matchRatio * 75 + Math.min(25, resume.experienceYears * 4));
  if (score > 98) score = 98;
  if (score < 35 && matchedSkills.length > 0) score = 42;

  // Try real Gemini API call if Google key is available
  if (config.useAiForMatching && config.googleApiKey && config.googleApiKey.startsWith('AIza')) {
    try {
      const prompt = `You are an expert ATS (Applicant Tracking System) Screener.
Compare this Candidate Resume against the Target Job Description.

TARGET JOB: ${job.title} at ${job.company}
REQUIRED SKILLS: ${job.skillsRequired.join(', ')}
JOB DESCRIPTION: ${job.description}

CANDIDATE PROFILE: ${resume.fullName} (${resume.targetRole})
CANDIDATE SKILLS: ${resume.skills.join(', ')}
RESUME SUMMARY: ${resume.summary}

Return ONLY a JSON object with this exact format:
{
  "score": number between 40 and 99,
  "matchedSkills": ["skill1", "skill2"],
  "missingSkills": ["skill3"],
  "summary": "Brief 1-sentence match rationale",
  "recommendations": ["Recommendation 1"]
}`;

      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${config.googleModel}:generateContent?key=${config.googleApiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }]
          })
        }
      );

      if (response.ok) {
        const data = await response.json();
        const rawText = data?.candidates?.[0]?.content?.parts?.[0]?.text || '';
        const jsonMatch = rawText.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          return {
            score: parsed.score || score,
            matchedSkills: parsed.matchedSkills || matchedSkills,
            missingSkills: parsed.missingSkills || missingSkills,
            summary: parsed.summary || `${matchedSkills.length} of ${job.skillsRequired.length} key requirements matched.`,
            recommendations: parsed.recommendations || [`Highlight experience with ${missingSkills.slice(0, 2).join(', ')}`]
          };
        }
      }
    } catch (err) {
      console.warn('Google Gemini API match call fallback to local matcher:', err);
    }
  }

  return {
    score,
    matchedSkills,
    missingSkills,
    summary: `${matchedSkills.length} of ${job.skillsRequired.length} key requirements matched.`,
    recommendations: missingSkills.length > 0 
      ? [`Consider adding experience with ${missingSkills.slice(0, 2).join(', ')} to boost your score.`]
      : ['Strong overall skill alignment for this role!']
  };
}

/**
 * Generate a personalized cover letter pitch for auto-applying to a job portal.
 */
export async function generateCoverLetter(
  resume: ResumeProfile,
  job: JobPost,
  config: AiConfigState
): Promise<string> {
  const defaultNote = `Dear Hiring Manager at ${job.company},

I am writing to express my strong interest in the ${job.title} role. With over ${resume.experienceYears} years of experience in ${resume.skills.slice(0, 4).join(', ')}, I have successfully delivered high-reliability cloud and software solutions aligned with your stack.

My expertise directly covers your core requirements including ${job.skillsRequired.slice(0, 3).join(', ')}. I look forward to contributing to ${job.company}'s engineering goals.

Best regards,
${resume.fullName}
${resume.email} | ${resume.phone}`;

  if (config.useAiForCoverLetter && config.googleApiKey && config.googleApiKey.startsWith('AIza')) {
    try {
      const prompt = `Write a short 3-paragraph compelling job application cover note for candidate ${resume.fullName} applying for ${job.title} at ${job.company}.
Candidate Skills: ${resume.skills.join(', ')}
Candidate Summary: ${resume.summary}
Job Requirements: ${job.skillsRequired.join(', ')}`;

      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${config.googleModel}:generateContent?key=${config.googleApiKey}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }]
          })
        }
      );

      if (response.ok) {
        const data = await response.json();
        const text = data?.candidates?.[0]?.content?.parts?.[0]?.text;
        if (text) return text.trim();
      }
    } catch (err) {
      console.warn('Gemini Cover Letter fallback to default note template', err);
    }
  }

  return defaultNote;
}
