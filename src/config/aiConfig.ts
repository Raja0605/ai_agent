import type { AiConfigState } from '../types/job';

const LOCAL_STORAGE_KEY = 'job_pulse_ai_config';

export const getDefaultAiConfig = (): AiConfigState => {
  return {
    activeProvider: 'google',
    googleApiKey: import.meta.env.VITE_GOOGLE_API_KEY || '',
    openaiApiKey: import.meta.env.VITE_OPENAI_API_KEY || '',
    googleModel: import.meta.env.VITE_GOOGLE_LLM_MODEL || 'gemini-3.1-pro-preview',
    openaiModel: import.meta.env.VITE_OPENAI_LLM_MODEL || 'gpt-5.6-terra',
    embeddingsModel: import.meta.env.VITE_EMBEDDINGS_MODEL || 'models/gemini-embedding-001',
    useAiForMatching: true,
    useAiForCoverLetter: true,
  };
};

export const getSavedAiConfig = (): AiConfigState => {
  try {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return { ...getDefaultAiConfig(), ...parsed };
    }
  } catch (err) {
    console.error('Failed to load AI config from localStorage', err);
  }
  return getDefaultAiConfig();
};

export const saveAiConfig = (config: AiConfigState): void => {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(config));
  } catch (err) {
    console.error('Failed to save AI config to localStorage', err);
  }
};
