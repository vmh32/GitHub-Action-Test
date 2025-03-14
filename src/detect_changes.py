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
    return [file['filename'] for file in response.json().get('files', [])]

def matches_pattern(file_path: str, patterns: List[str]) -> bool:
    """Check if file path matches any of the glob patterns."""
    return any(fnmatch.fnmatch(file_path, pattern) for pattern in patterns)

def detect_changes(projects: Dict, changed_files: List[str]) -> Set[str]:
    """Detect which projects were modified based on changed files."""
    modified_projects = set()
    for project_id, config in projects.items():
        if any(matches_pattern(file, pattern) for file in changed_files for pattern in config['patterns']):
            modified_projects.add(project_id)
    return modified_projects

def order_projects(projects: Dict, modified_projects: Set[str]) -> List[str]:
    """Order projects by dependencies."""
    ordered = []
    visited = set()
    visiting = set()

    def visit(project_id: str):
        """DFS visit with cycle detection."""
        if project_id in visited:
            return
        if project_id in visiting:
            sys.exit(f"Error: Circular dependency detected involving {project_id}")

        visiting.add(project_id)
        for dep in projects[project_id]['dependencies']:
            if dep in modified_projects:
                visit(dep)
        visiting.remove(project_id)
        visited.add(project_id)
        ordered.append(project_id)

    for project_id in modified_projects:
        visit(project_id)

    return ordered

def main():
    """Main function."""
    try:
        # Get inputs
        token = get_github_token()
        projects_json = os.environ.get('INPUT_PROJECTS')
        if not projects_json:
            sys.exit("Error: INPUT_PROJECTS environment variable is required")

        # Parse projects configuration
        projects = json.loads(projects_json)

        # Get changed files
        changed_files = get_changed_files(token)
        print(f"Debug: Changed files: {changed_files}")

        # Detect modified projects
        modified_projects = detect_changes(projects, changed_files)
        print(f"Debug: Modified projects: {modified_projects}")

        # Order projects by dependencies
        ordered_projects = order_projects(projects, modified_projects)
        print(f"Debug: Ordered projects: {ordered_projects}")

        # Check if any modified project uses nuspec
        has_nuspec = any(projects[pid]['path'].endswith('.nuspec') for pid in modified_projects)

        # Set outputs using GitHub Actions environment file
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"modified_packages={json.dumps(list(modified_projects))}\n")
            f.write(f"ordered_changes={json.dumps(ordered_projects)}\n")
            f.write(f"has_nuspec={str(has_nuspec).lower()}\n")

    except Exception as e:
        sys.exit(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 