#!/bin/bash
# Keeps the 5 most recent images in each Artifact Registry repo and deletes the rest.
PROJECT="mentors-mantra-gen"
KEEP=5

cleanup_repo() {
    local REPO=$1
    echo ""
    echo "=== Cleaning: $REPO ==="
    DIGESTS=$(gcloud artifacts docker images list "$REPO" \
        --sort-by=~CREATE_TIME \
        --format="get(digest)" 2>/dev/null | tail -n +$((KEEP + 1)))

    if [ -z "$DIGESTS" ]; then
        echo "  Nothing to delete (≤ $KEEP images present)."
        return
    fi

    while IFS= read -r digest; do
        if [ -n "$digest" ]; then
            echo "  Deleting $digest ..."
            gcloud artifacts docker images delete "${REPO}@${digest}" --quiet --delete-tags 2>&1
        fi
    done <<< "$DIGESTS"
    echo "  Done."
}

cleanup_repo "us-docker.pkg.dev/$PROJECT/gcr.io/mentors-mantra-api"
cleanup_repo "us-central1-docker.pkg.dev/$PROJECT/cloud-run-source-deploy/mentors-mantra-api"

echo ""
echo "Cleanup complete!"
