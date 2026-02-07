#!/bin/bash

# EC2 Deployment Script for Manim Worker

# 1. Install Docker & Git
sudo apt-get update
sudo apt-get install -y docker.io git

# 2. Clone Repository (User needs to provide repo URL)
# git clone https://github.com/your-repo/infinitest.git
# cd infinitest

# 3. Create .env file for worker
cat <<EOF > .env.worker
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
AWS_REGION=ap-south-1
S3_BUCKET_NAME=infinitest-videos
SQS_QUEUE_URL=${SQS_QUEUE_URL}
EOF

# 4. Build Docker Image
sudo docker build -t manim-worker -f docker/Dockerfile.manim .

# 5. Run Worker
sudo docker run -d \
    --name video-worker \
    --restart unless-stopped \
    --env-file .env.worker \
    manim-worker

echo "Worker deployed successfully!"
