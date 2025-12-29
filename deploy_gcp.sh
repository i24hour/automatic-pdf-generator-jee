#!/bin/bash

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo "🚀 Deploying Mentors Mantra API to Google Cloud Run..."

# Set project if needed (uncomment and replace)
# gcloud config set project mentors-mantra-pdf

# Deploy
gcloud run deploy mentors-mantra-api \
  --source ./backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --timeout=300 \
  --memory=1Gi

echo "✅ Deployment initiated!"
