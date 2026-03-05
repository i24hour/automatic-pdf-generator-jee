#!/bin/bash
PROJECT="mentors-mantra-gen"

echo "Cleaning up us.gcr.io/mentors-mantra-api..."
gcloud artifacts docker images list us-docker.pkg.dev/$PROJECT/gcr.io/mentors-mantra-api \
    --sort-by=~CREATE_TIME --format="value(digest)" | tail -n +6 | while read digest; do
    echo "Deleting $digest..."
    gcloud artifacts docker images delete "us-docker.pkg.dev/$PROJECT/gcr.io/mentors-mantra-api@$digest" --quiet --delete-tags
done

echo "Cleaning up cloud-run-source-deploy..."
gcloud artifacts docker images list us-central1-docker.pkg.dev/$PROJECT/cloud-run-source-deploy/mentors-mantra-api \
    --sort-by=~CREATE_TIME --format="value(digest)" | tail -n +6 | while read digest; do
    echo "Deleting $digest..."
    gcloud artifacts docker images delete "us-central1-docker.pkg.dev/$PROJECT/cloud-run-source-deploy/mentors-mantra-api@$digest" --quiet --delete-tags
done
