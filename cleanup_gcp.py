import subprocess
import json

PROJECT = "mentors-mantra-gen"
KEEP = 5

def clean_repo(repo_path):
    print(f"\nScanning repository: {repo_path}")
    
    # List images
    cmd = f"gcloud artifacts docker images list {repo_path} --sort-by=~CREATE_TIME --format=json"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error listing images: {result.stderr}")
        return
        
    try:
        images = json.loads(result.stdout)
    except:
        print("Failed to parse JSON")
        return
        
    print(f"Found {len(images)} images.")
    
    if len(images) <= KEEP:
        print(f"Keeping all {len(images)} images. Nothing to delete.")
        return
        
    to_delete = images[KEEP:]
    print(f"Deleting {len(to_delete)} old images...")
    
    for img in to_delete:
        # The fully qualified package path
        pkg = img['package']
        version = img['version']
        full_path = f"{pkg}@{version}"
        
        print(f"Deleting: {full_path}")
        del_cmd = f"gcloud artifacts docker images delete {full_path} --delete-tags --quiet"
        del_result = subprocess.run(del_cmd, shell=True, capture_output=True, text=True)
        if del_result.returncode == 0:
            print("  ✓ Deleted")
        else:
            print(f"  ✗ Failed: {del_result.stderr.strip()}")

if __name__ == "__main__":
    # Repository 1: gcr.io inside us-docker
    clean_repo(f"us-docker.pkg.dev/{PROJECT}/gcr.io/mentors-mantra-api")
    
    # Repository 2: cloud-run-source-deploy
    clean_repo(f"us-central1-docker.pkg.dev/{PROJECT}/cloud-run-source-deploy/mentors-mantra-api")
