#!/usr/bin/env python3
"""
Script to mark Story 5B subtasks as complete in Asana
"""

import requests
import json
from datetime import datetime

# Load configuration
with open('mcp_asana_config.json', 'r') as f:
    config = json.load(f)

# Asana API configuration
ASANA_API_BASE = "https://app.asana.com/api/1.0"
PAT_TOKEN = config['auth']['pat_token']
HEADERS = {
    'Authorization': f'Bearer {PAT_TOKEN}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

# Subtasks to mark complete
SUBTASKS_TO_COMPLETE = {
    "1210701775866910": "Build intelligence endpoints (3 hours)",
    "1210701650139753": "Extend FastAPI app (2 hours)",
    "1210715661962382": "Implement authentication on all endpoints (1 hour)"
}

def mark_task_complete(task_gid, task_name):
    """Mark a task as complete and add a comment"""
    
    # First, mark the task as complete
    task_url = f"{ASANA_API_BASE}/tasks/{task_gid}"
    update_data = {
        "data": {
            "completed": True
        }
    }
    
    print(f"\nMarking '{task_name}' as complete...")
    response = requests.put(task_url, headers=HEADERS, json=update_data)
    
    if response.status_code == 200:
        print(f"✓ Successfully marked task as complete")
        
        # Add a comment to the task
        comment_url = f"{ASANA_API_BASE}/tasks/{task_gid}/stories"
        comment_data = {
            "data": {
                "text": "Task completed. This has been implemented and is ready for deployment."
            }
        }
        
        comment_response = requests.post(comment_url, headers=HEADERS, json=comment_data)
        
        if comment_response.status_code == 201:
            print(f"✓ Added completion note to task")
        else:
            print(f"✗ Error adding comment: {comment_response.status_code} - {comment_response.text}")
            
    else:
        print(f"✗ Error marking task complete: {response.status_code} - {response.text}")
        
    return response.status_code == 200

def main():
    print("=== Marking Story 5B Subtasks as Complete ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Using PAT token: {PAT_TOKEN[:20]}...")
    
    successful_updates = 0
    total_tasks = len(SUBTASKS_TO_COMPLETE)
    
    for task_gid, task_name in SUBTASKS_TO_COMPLETE.items():
        if mark_task_complete(task_gid, task_name):
            successful_updates += 1
    
    print("\n=== Summary ===")
    print(f"Total tasks: {total_tasks}")
    print(f"Successfully updated: {successful_updates}")
    print(f"Failed: {total_tasks - successful_updates}")
    
    if successful_updates == total_tasks:
        print("\n✅ All Story 5B subtasks have been marked as complete!")
    else:
        print("\n⚠️  Some tasks failed to update. Please check the errors above.")

if __name__ == "__main__":
    main()