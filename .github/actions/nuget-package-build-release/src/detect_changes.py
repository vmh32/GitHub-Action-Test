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
    """Get list of changed files in the pull request or push."""
    print("Getting changed files...")
    
    # Get required environment variables
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path:
        sys.exit("Error: GITHUB_EVENT_PATH environment variable is required")

    # Read event data
    with open(event_path) as f:
        event_data = json.load(f)

    # Extract repository information
    repo_full_name = event_data['repository']['full_name']

    # Handle different event types
    event_name = os.environ.get('GITHUB_EVENT_NAME', '')
    print(f"Event type: {event_name}")

    if event_name == 'pull_request':
        base_sha = event_data['pull_request']['base']['sha']
        head_sha = event_data['pull_request']['head']['sha']
    elif event_name == 'push':
        base_sha = event_data['before']
        head_sha = event_data['after']
    else:
        sys.exit(f"Error: Unsupported event type: {event_name}")

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

def detect_changes(projects: Dict, changed_files: List[str]) -> tuple[Set[str], bool]:
    """Detect which projects were modified based on changed files."""
    print("Detecting project changes...")
    modified_projects = set()
    has_nuspec = False
    
    # Create mapping from project_id to key
    key_map = {project_id: f"X{idx+1}" for idx, (project_id, _) in enumerate(sorted(projects.items()))}
    print(f"Project to key mapping: {key_map}")
    
    for file_path in changed_files:
        for project_id, config in projects.items():
            if matches_pattern(file_path, config['patterns']):
                print(f"Project {project_id} was modified by {file_path}")
                key = key_map[project_id]
                modified_projects.add(key)
                if config['path'].endswith('.nuspec'):
                    has_nuspec = True
                break  # Move to next file once we find a matching project
    
    print(f"Modified projects (with keys): {modified_projects}")
    return modified_projects, has_nuspec

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
        modified_projects, has_nuspec = detect_changes(projects, changed_files)
        print(f"Modified projects: {modified_projects}")

        # Set outputs in GitHub Actions format
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            modified_list = list(modified_projects)
            f.write(f"changes={json.dumps(modified_list)}\n")
            f.write(f"modified_packages={json.dumps(modified_list)}\n")
            f.write(f"ordered_changes={json.dumps(modified_list)}\n")  # We'll let the next step handle ordering
            f.write(f"has_nuspec={str(has_nuspec).lower()}\n")

        print("Change detection completed successfully")

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        sys.exit(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 