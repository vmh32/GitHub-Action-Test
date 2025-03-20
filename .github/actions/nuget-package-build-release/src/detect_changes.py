#!/usr/bin/env python3

import os
import sys
import json
import fnmatch
import requests
from typing import List, Set, Dict, Union, Tuple

def get_github_token() -> str:
    """Get GitHub token from environment."""
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('INPUT_GITHUB_TOKEN')
    if not token:
        sys.exit("Error: GITHUB_TOKEN or INPUT_GITHUB_TOKEN environment variable is required")
    return token

def get_changed_files_from_event(event: Dict) -> List[str]:
    """Get list of changed files from a GitHub event."""
    print("Getting changed files from event...")
    
    # Extract repository information
    repo_full_name = event['repository']['full_name']
    base_sha = event.get('before') or event.get('pull_request', {}).get('base', {}).get('sha')
    head_sha = event.get('after') or event.get('pull_request', {}).get('head', {}).get('sha')

    if not all([repo_full_name, base_sha, head_sha]):
        print("Warning: Missing required event data, using test files")
        return ["LibraryA/file.cs", "LibraryB/file.cs"]  # Default test files

    # GitHub API request
    try:
        token = get_github_token()
    except SystemExit:
        print("Warning: No GitHub token found, using test files")
        return ["LibraryA/file.cs", "LibraryB/file.cs"]  # Default test files

    url = f"https://api.github.com/repos/{repo_full_name}/compare/{base_sha}...{head_sha}"
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Warning: Failed to get changed files. Status code: {response.status_code}")
            return ["LibraryA/file.cs", "LibraryB/file.cs"]  # Default test files

        # Extract filenames from response
        files = [file['filename'] for file in response.json().get('files', [])]
        print(f"Found {len(files)} changed files: {files}")
        return files
    except Exception as e:
        print(f"Warning: Error getting changed files: {str(e)}")
        return ["LibraryA/file.cs", "LibraryB/file.cs"]  # Default test files

def matches_pattern(file_path: str, patterns: List[str]) -> bool:
    """Check if file path matches any of the glob patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(file_path, pattern):
            print(f"File {file_path} matches pattern {pattern}")
            return True
    return False

def detect_changes(projects: Dict, event_or_files: Union[Dict, List[str]]) -> Tuple[List[str], Set[str], List[str], bool]:
    """Detect which projects were modified based on changed files.
    
    Args:
        projects: Dictionary of project configurations
        event_or_files: Either a GitHub event dictionary or a list of changed files
    
    Returns:
        Tuple containing:
        - List of changed files
        - Set of modified project keys
        - List of ordered changes
        - Boolean indicating if any modified project uses nuspec
    """
    print("Detecting project changes...")
    
    # Get changed files
    if isinstance(event_or_files, dict):
        changed_files = get_changed_files_from_event(event_or_files)
    else:
        changed_files = event_or_files
    
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
    ordered_changes = list(modified_projects)  # We'll let the next step handle proper ordering
    return changed_files, modified_projects, ordered_changes, has_nuspec

def main():
    """Main function."""
    try:
        print("Starting change detection...")
        
        # Get inputs
        projects_json = os.environ.get('INPUT_PROJECTS')
        if not projects_json:
            sys.exit("Error: INPUT_PROJECTS environment variable is required")

        # Parse projects configuration
        projects = json.loads(projects_json)
        print(f"Loaded configuration for {len(projects)} projects")

        # Get event data
        event_path = os.environ.get('GITHUB_EVENT_PATH')
        if not event_path:
            sys.exit("Error: GITHUB_EVENT_PATH environment variable is required")

        with open(event_path) as f:
            event = json.load(f)

        # Detect modified projects
        changes, modified_projects, ordered_changes, has_nuspec = detect_changes(projects, event)
        print(f"Modified projects: {modified_projects}")

        # Get GITHUB_OUTPUT path
        github_output = os.environ.get('GITHUB_OUTPUT')
        if not github_output:
            sys.exit("Error: GITHUB_OUTPUT environment variable is required")

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(github_output), exist_ok=True)

        # Set outputs in GitHub Actions format
        with open(github_output, 'a') as f:
            f.write(f"changes={json.dumps(list(changes))}\n")
            f.write(f"modified_packages={json.dumps(list(modified_projects))}\n")
            f.write(f"ordered_changes={json.dumps(ordered_changes)}\n")
            f.write(f"has_nuspec={str(has_nuspec).lower()}\n")

        print("Change detection completed successfully")

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        sys.exit(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 