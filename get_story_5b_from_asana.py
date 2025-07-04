#!/usr/bin/env python3
"""
Script to retrieve Story 5B and its subtasks from Asana
Uses the Asana API directly with Personal Access Token
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
    'Accept': 'application/json'
}

def search_for_story_5b():
    """Search for Story 5B across all workspaces and projects"""
    
    # First, get all workspaces
    workspaces_url = f"{ASANA_API_BASE}/workspaces"
    response = requests.get(workspaces_url, headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Error getting workspaces: {response.status_code} - {response.text}")
        return
    
    workspaces = response.json()['data']
    print(f"Found {len(workspaces)} workspace(s)")
    
    for workspace in workspaces:
        print(f"\nSearching workspace: {workspace['name']} ({workspace['gid']})")
        
        # Search for tasks containing "5B" or "Story 5B"
        search_url = f"{ASANA_API_BASE}/workspaces/{workspace['gid']}/tasks/search"
        search_params = {
            'text': 'Story 5B API endpoints',
            'opt_fields': 'name,notes,completed,created_at,modified_at,due_on,assignee.name,projects.name,parent,custom_fields'
        }
        
        response = requests.get(search_url, headers=HEADERS, params=search_params)
        
        if response.status_code == 200:
            tasks = response.json()['data']
            print(f"Found {len(tasks)} task(s) matching 'Story 5B'")
            
            for task in tasks:
                print_task_details(task)
                
                # Get subtasks if this is a parent task
                if task.get('gid'):
                    get_subtasks(task['gid'])
        else:
            print(f"Error searching tasks: {response.status_code} - {response.text}")

def print_task_details(task):
    """Print task details in a formatted way"""
    print("\n" + "="*80)
    print(f"Task: {task.get('name', 'Unnamed')}")
    print(f"ID: {task.get('gid', 'No ID')}")
    print(f"Completed: {task.get('completed', False)}")
    
    if task.get('assignee'):
        print(f"Assignee: {task['assignee'].get('name', 'Unassigned')}")
    
    if task.get('due_on'):
        print(f"Due: {task['due_on']}")
    
    if task.get('projects'):
        projects = [p.get('name', 'Unnamed') for p in task['projects']]
        print(f"Projects: {', '.join(projects)}")
    
    if task.get('notes'):
        print(f"\nNotes:\n{task['notes'][:500]}{'...' if len(task.get('notes', '')) > 500 else ''}")
    
    print("="*80)

def get_subtasks(parent_task_gid):
    """Get all subtasks for a parent task"""
    subtasks_url = f"{ASANA_API_BASE}/tasks/{parent_task_gid}/subtasks"
    params = {
        'opt_fields': 'name,notes,completed,created_at,modified_at,due_on,assignee.name'
    }
    
    response = requests.get(subtasks_url, headers=HEADERS, params=params)
    
    if response.status_code == 200:
        subtasks = response.json()['data']
        if subtasks:
            print(f"\n--- Subtasks ({len(subtasks)} found) ---")
            for subtask in subtasks:
                print(f"\n  • {subtask.get('name', 'Unnamed')}")
                print(f"    ID: {subtask.get('gid', 'No ID')}")
                print(f"    Completed: {subtask.get('completed', False)}")
                if subtask.get('assignee'):
                    print(f"    Assignee: {subtask['assignee'].get('name', 'Unassigned')}")
                if subtask.get('due_on'):
                    print(f"    Due: {subtask['due_on']}")
                
                # Get full subtask details including notes
                if subtask.get('gid'):
                    get_task_full_details(subtask['gid'])
    else:
        print(f"Error getting subtasks: {response.status_code} - {response.text}")

def get_task_full_details(task_gid):
    """Get full details of a specific task including notes"""
    task_url = f"{ASANA_API_BASE}/tasks/{task_gid}"
    params = {
        'opt_fields': 'name,notes,completed,created_at,modified_at,due_on,assignee.name,custom_fields'
    }
    
    response = requests.get(task_url, headers=HEADERS, params=params)
    
    if response.status_code == 200:
        task = response.json()['data']
        if task.get('notes'):
            print(f"    Notes: {task['notes'][:200]}{'...' if len(task.get('notes', '')) > 200 else ''}")
    else:
        print(f"Error getting task details: {response.status_code} - {response.text}")

def main():
    print("Searching for Story 5B in Asana...")
    print(f"Using PAT token: {PAT_TOKEN[:20]}...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    search_for_story_5b()
    
    print("\n\nSearch complete!")

if __name__ == "__main__":
    main()