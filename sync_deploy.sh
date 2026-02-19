#!/bin/bash
echo "🔄 Syncing changes to Vercel-connected repository..."

# The Vercel project is linked to this repository
TARGET_REPO="https://github.com/priyanshu85953s/automatic-pdf-generator-jee.git"

# Check if we can access the remote
echo "Checking connection to $TARGET_REPO..."

# Add remote if it doesn't exist
if ! git remote | grep -q "production"; then
    git remote add production $TARGET_REPO
fi

# Attempt push
echo "🚀 Pushing to production remote..."
echo "⚠️  You may be asked to enter your GitHub Username and Password/Token"
git push production main

if [ $? -eq 0 ]; then
    echo "✅ Success! Changes pushed. Vercel deployment should start immediately."
    echo "Check status here: https://vercel.com/priyanshu85953s-projects/mentors-mantra-test-generator"
else
    echo "❌ Push failed."
    echo "Make sure you have write access to 'priyanshu85953s/automatic-pdf-generator-jee'"
fi
