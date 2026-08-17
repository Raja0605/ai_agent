# JobPulse Architecture

## Overview
JobPulse follows a modular architecture integrating a React Frontend, a FastAPI Backend, and a PostgreSQL database.

```text
React Frontend
      |
      v
FastAPI Backend
      |
      v
Job Aggregation Layer -> Remotive/Adzuna (External APIs)
      |
      v
Job Database (PostgreSQL)
      |
      v
User CV & Preferences
      |
      v
AI Job Matching (Gemini)
      |
      v
Application Tracking
```

## Backend Services
- **Job Service**: Deduplicates and stores canonical jobs into Postgres.
- **Source Manager**: Concurrently fetches jobs using `httpx`.
- **AI Service**: Matches candidate CVs to job descriptions using LLMs.
- **Application Service**: Stores user interactions and apply workflows.

## Auto-Apply Flow
Auto-apply currently aids the user by parsing CVs, calculating an ATS score, and generating a custom cover letter via the AI Service, before opening the live job application URL for the user to complete manually, ensuring compliance with CAPTCHA and Terms of Service.
