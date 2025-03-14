import * as core from '@actions/core';
import * as github from '@actions/github';
import { exec } from '@actions/exec';
import * as path from 'path';

interface ProjectConfig {
  path: string;
  patterns: string[];
  dependencies: string[];
}

interface ProjectMap {
  [key: string]: ProjectConfig;
}

async function getChangedFiles(): Promise<string[]> {
  const token = core.getInput('github_token', { required: true });
  const octokit = github.getOctokit(token);
  const context = github.context;

  // Get the base and head SHAs
  const baseSha = context.payload.pull_request?.base?.sha;
  const headSha = context.payload.pull_request?.head?.sha;

  if (!baseSha || !headSha) {
    throw new Error('Could not determine base or head SHA');
  }

  // Get the list of changed files
  const response = await octokit.rest.repos.compareCommits({
    owner: context.repo.owner,
    repo: context.repo.repo,
    base: baseSha,
    head: headSha,
  });

  return response.data.files?.map(file => file.filename) || [];
}

function matchesPattern(filePath: string, patterns: string[]): boolean {
  return patterns.some(pattern => {
    // Convert glob pattern to regex
    const regexPattern = pattern
      .replace(/\*/g, '.*')
      .replace(/\?/g, '.')
      .replace(/\//g, '\\/');
    const regex = new RegExp(`^${regexPattern}$`);
    return regex.test(filePath);
  });
}

async function run(): Promise<void> {
  try {
    // Parse projects configuration
    const projectsInput = core.getInput('projects', { required: true });
    const projects: ProjectMap = JSON.parse(projectsInput);

    // Get changed files
    const changedFiles = await getChangedFiles();
    core.debug(`Changed files: ${JSON.stringify(changedFiles)}`);

    // Detect which projects were modified
    const modifiedProjects = new Set<string>();
    for (const [projectId, config] of Object.entries(projects)) {
      for (const file of changedFiles) {
        if (matchesPattern(file, config.patterns)) {
          modifiedProjects.add(projectId);
          break;
        }
      }
    }

    // Order projects by dependencies
    const orderedProjects: string[] = [];
    const visited = new Set<string>();
    const visiting = new Set<string>();

    function visit(projectId: string) {
      if (visited.has(projectId)) return;
      if (visiting.has(projectId)) {
        throw new Error(`Circular dependency detected involving ${projectId}`);
      }

      visiting.add(projectId);
      const config = projects[projectId];
      for (const dep of config.dependencies) {
        if (modifiedProjects.has(dep)) {
          visit(dep);
        }
      }
      visiting.delete(projectId);
      visited.add(projectId);
      orderedProjects.push(projectId);
    }

    for (const projectId of modifiedProjects) {
      visit(projectId);
    }

    // Check if any modified project uses nuspec
    const hasNuspec = Array.from(modifiedProjects).some(
      projectId => projects[projectId].path.endsWith('.nuspec')
    );

    // Set outputs
    core.setOutput('modified_packages', JSON.stringify(Array.from(modifiedProjects)));
    core.setOutput('ordered_changes', JSON.stringify(orderedProjects));
    core.setOutput('has_nuspec', hasNuspec.toString());

    // Debug output
    core.debug(`Modified packages: ${Array.from(modifiedProjects).join(', ')}`);
    core.debug(`Ordered changes: ${orderedProjects.join(', ')}`);
    core.debug(`Has nuspec: ${hasNuspec}`);

  } catch (error) {
    if (error instanceof Error) {
      core.setFailed(error.message);
    } else {
      core.setFailed('An unexpected error occurred');
    }
  }
}

run(); 