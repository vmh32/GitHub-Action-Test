#!/usr/bin/env python3

import os
import sys
import json
import fnmatch
import requests
from typing import List, Set, Dict

def get_github_token() -> str:
    """Get GitHub token from environment."""
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        sys.exit("Error: GITHUB_TOKEN environment variable is required")
    return token

def get_changed_files(token: str) -> List[str]:
    """Get list of changed files in the pull request."""
    print("Getting changed files...")
    
    # Get required environment variables
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path:
        sys.exit("Error: GITHUB_EVENT_PATH environment variable is required")

    # Read event data
    with open(event_path) as f:
        event_data = json.load(f)

    # Extract repository and PR information
    repo_full_name = event_data['repository']['full_name']
    base_sha = event_data['pull_request']['base']['sha']
    head_sha = event_data['pull_request']['head']['sha']

    print(f"Comparing changes between {base_sha} and {head_sha}")

    # GitHub API request
    url = f"https://api.github.com/repos/{repo_full_name}/compare/{base_sha}...{head_sha}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        sys.exit(f"Error: Failed to get changed files. Status code: {response.status_code}")

    # Extract filenames from response
    files = [file['filename'] for file in response.json().get('files', [])]
    print(f"Found {len(files)} changed files: {files}")
    return files

def matches_pattern(file_path: str, patterns: List[str]) -> bool:
    """Check if file path matches any of the glob patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(file_path, pattern):
            print(f"File {file_path} matches pattern {pattern}")
            return True
    return False

def detect_changes(projects: Dict, changed_files: List[str]) -> Set[str]:
    """Detect which projects were modified based on changed files."""
    print("Detecting project changes...")
    modified_projects = set()
    
    for file_path in changed_files:
        for project_id, config in projects.items():
            if matches_pattern(file_path, config['patterns']):
                print(f"Project {project_id} was modified by {file_path}")
                modified_projects.add(project_id)
                break  # Move to next file once we find a matching project
    
    return modified_projects

def main():
    """Main function."""
    try:
        print("Starting change detection...")
        
        # Get inputs
        token = get_github_token()
        projects_json = os.environ.get('INPUT_PROJECTS')
        if not projects_json:
            sys.exit("Error: INPUT_PROJECTS environment variable is required")

        # Parse projects configuration
        projects = json.loads(projects_json)
        print(f"Loaded configuration for {len(projects)} projects")

        # Get changed files
        changed_files = get_changed_files(token)

        # Detect modified projects
        modified_projects = detect_changes(projects, changed_files)
        print(f"Modified projects: {modified_projects}")

        # Set output in dorny format
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"changes={json.dumps(list(modified_projects))}\n")

        print("Change detection completed successfully")

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        sys.exit(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 