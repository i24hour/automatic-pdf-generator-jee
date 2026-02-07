import os
import asyncio
from services.aws_services import get_aws_services
from dotenv import load_dotenv

load_dotenv()

async def test_aws():
    print("Testing AWS S3 and SQS connection...")
    aws = get_aws_services()
    
    # Test S3 List (to verify access)
    try:
        print(f"Checking bucket: {aws.bucket_name}")
        # Just try to list objects to verify permissions
        response = await asyncio.to_thread(aws.s3_client.list_objects_v2, Bucket=aws.bucket_name, MaxKeys=1)
        print("✅ S3 Connection Successful!")
    except Exception as e:
        print(f"❌ S3 Failed: {e}")

    # Test SQS Send
    try:
        print(f"Sending test message to: {aws.queue_url}")
        success = await aws.send_job_to_queue({"test": "true", "job_id": "test-123"})
        if success:
            print("✅ SQS Send Successful!")
        else:
            print("❌ SQS Send Failed!")
    except Exception as e:
        print(f"❌ SQS Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_aws())
