# Deploying to Google Cloud Run

Google Cloud Run is a serverless platform that can run your Docker container with **no timeout limits** (up to 60 minutes), making it perfect for your PDF generator.

## Prerequisites

1.  **Google Cloud Account**: [Sign up here](https://cloud.google.com/) (Free trial includes $300 credits).
2.  **gcloud CLI**: [Install here](https://cloud.google.com/sdk/docs/install).

## Deployment Steps

### 1. Login to Google Cloud

Open your terminal and run:

```bash
gcloud auth login
```

### 2. Create a Project

Create a new project (or use an existing one):

```bash
# Create a project named "mentors-mantra-pdf"
gcloud projects create mentors-mantra-pdf --name="Mentors Mantra PDF"

# Set it as current project
gcloud config set project mentors-mantra-pdf
```

### 3. Enable Required Services

Enable Cloud Run and Artifact Registry:

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
```

### 4. Deploy

Run this single command to build and deploy your backend:

```bash
gcloud run deploy mentors-mantra-api \
  --source ./backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=YOUR_DATABASE_URL,JWT_SECRET_KEY=YOUR_SECRET_KEY,GOOGLE_API_KEY=YOUR_GEMINI_KEY,SMTP_PASSWORD=YOUR_GMAIL_APP_PASSWORD"
```

**Replace the environment variables with your actual values:**
- `DATABASE_URL`: Your PostgreSQL URL (you can keep using the Heroku one or set up a new one).
- `JWT_SECRET_KEY`: Your secret key.
- `GOOGLE_API_KEY`: Your Gemini API key.
- `SMTP_PASSWORD`: Your Gmail App Password.

### 5. Update Frontend

Once deployed, you will get a Service URL (e.g., `https://mentors-mantra-api-xyz.a.run.app`).

1.  Go to Vercel dashboard.
2.  Select your frontend project.
3.  Go to **Settings > Environment Variables**.
4.  Update `NEXT_PUBLIC_API_URL` to your new Cloud Run URL.
5.  Redeploy the frontend.

## Troubleshooting

-   **Timeouts**: Cloud Run defaults to 5 minutes timeout, which is plenty. You can increase it up to 60 mins if needed:
    ```bash
    gcloud run services update mentors-mantra-api --timeout=3600
    ```
