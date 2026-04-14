# iHire Codebase Brief

## Overview
**iHire** (Hiring Intelligence System) is a production-grade, multi-agent AI system designed for automated resume screening and candidate ranking. It evaluates candidate resumes against a provided Job Description (JD) using multiple specialized AI agents, synthesizing the results to generate actionable verdicts and automated feedback.

## Architecture

The project is structured into two main components:

### 1. Backend API (Node.js & TypeScript)
Located primarily in the `src/` directory at the project root, this handles the core AI orchestration.
- **Entry Point (`src/index.ts`)**: Sets up a health check server and initializes the orchestration loop, polling Google Drive for new resumes.
- **Orchestration (`src/workflow/orchestrator.ts`)**: The brain of the system. It processes the JD first, and for every new resume, it sequentially triggers text extraction, all 6 AI agents, verdict synthesis, saving results to Google Sheets, and sending emails.
- **AI Agents (`src/agents/`)**: Specialized tools extending a `BaseAgent` class:
  1. `jd-reality-agent`: Extracts the actual core work, non-negotiable skills, and pressure/ambiguity levels from the JD.
  2. `resume-structuring-agent`: Parses the candidate's PDF and extracts structured data (skills, projects, work experience) using both Regex (for contact info) and LLMs.
  3. `technical-checking-agent`: Evaluates the candidate's technical/execution fit based on the parsed JD and Resume.
  4. `founder-confidence-agent`: Evaluates soft skills and startup metrics (e.g. ownership, ambiguity handling).
  5. `assignment-generation-agent`: Generates a specialized technical assignment based on the JD.
  6. `candidate-feedback-agent`: Formulates feedback for the candidate based on evaluations.
- **Synthesis (`src/synthesis/`)**: Computes relevance scores and handles ultimate pass/fail logic using thresholds.
- **Integrations (`src/integrations/`)**: Handles specific third-party APIs: Google Drive (polling resumes), Google Sheets (leaderboard output), Nodemailer, and LiteLLM/Gemini (AI model interface).

### 2. Frontend (Next.js & React)
Located in the `frontend/` directory, this serves as the user dashboard.
- Uses Next.js (App Router), React 19, TailwindCSS v4, and Radix UI.
- Displays different routes/dashboards (`dashboard`, `candidate`, `ideas`, `itime`, `ichain`, `sf-tracker`).
- It has authentication built in (`next-auth`, `@auth/core`) and connects to diverse data sources like MongoDB and Supabase.
- Configured for cross-platform deployment via **Capacitor** allowing it to be compiled into an Android App in addition to a web application deployed to Vercel.

## Deployment Strategy
- **Backend**: Configured for Railway deployment (uses `Dockerfile` and `railway.json`). Driven largely via environment parameters (API Keys for Google and Gemini).
- **Frontend**: Configured for Vercel for the web application and Capacitor for Android App endpoints.

## Summary
The codebase is a well-structured modern Node/Next.js stack that leverages AI pipelines thoughtfully—breaking down the complex evaluation of candidates into multiple discrete agentic steps rather than replying on a single monolithic prompt. This allows for rigorous explainability and automated scoring.
