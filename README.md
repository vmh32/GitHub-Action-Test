# NuGet Package Version Management Action

This GitHub Action automates the versioning and publishing of NuGet packages in a multi-library solution. It detects changes in specified libraries, updates their versions based on PR comments, manages dependencies, and publishes the packages to GitHub Packages.

## How It Works

The action triggers when:
1. A pull request is opened or reopened
2. The target branch matches the specified branch (e.g., `qa`)
3. The PR branch name follows the format `Release.#.#.#` (e.g., `Release.1.6.0`)
4. Changes are detected in monitored library paths

### NuGet Package Source Configuration

To use the packages in Visual Studio and local development:

1. **Visual Studio Configuration**:
   - Open Visual Studio
   - Go to Tools > NuGet Package Manager > Package Manager Settings
   - Click on Package Sources
   - Click the plus icon to add a new source
   - Set Name: `GitHub Packages`
   - Set Source: `https://nuget.pkg.github.com/OWNER/index.json` (replace OWNER with your GitHub username or organization)
   - Click "Update" to save

2. **Authentication Setup**:
   - Create a Personal Access Token (PAT) in GitHub with `read:packages` scope
   - In Visual Studio's Package Sources, click "Update"
   - Enter your GitHub username and PAT when prompted
   
3. **Command Line Configuration**:
   ```powershell
   dotnet nuget add source "https://nuget.pkg.github.com/OWNER/index.json" ^
     --name "GitHub Packages" ^
     --username USERNAME ^
     --password PAT ^
     --store-password-in-clear-text
   ```

For more details, see [Working with the NuGet registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-nuget-registry)

### Branch Configuration

Modify the workflow trigger to match your target branch:
```yaml
on:
  pull_request:
    types: [opened, reopened]
    branches: [ qa ]  # Change this to your target branch
    paths:
      - 'LibraryA/**'
      - 'LibraryB/**'
      - 'LibraryC/**'
      - 'LibraryD/**'
```

### Development Workflow

This action supports a robust development workflow using the `UseNuGetReferences` property:

1. **Local Development & DEV Environment**:
   - Uses project references by default (`UseNuGetReferences=false`)
   - Enables direct debugging and real-time code changes
   - Example project structure:
   ```xml
   <!-- Set default value for UseNuGetReferences -->
   <PropertyGroup>
     <UseNuGetReferences Condition="'$(UseNuGetReferences)' == ''">false</UseNuGetReferences>
   </PropertyGroup>

   <ItemGroup>
     <ProjectReference Include="..\LibraryB\LibraryB.csproj" />
     <ProjectReference Include="..\LibraryC\LibraryC.csproj" />
   </ItemGroup>
   ```

2. **QA, UAT, and Production Environments**:
   - Uses NuGet package references (`UseNuGetReferences=true`)
   - Ensures consistent versioning across environments
   - Tests the exact packages that will go to production
   
To support this workflow, structure your project files like this:
```xml
<!-- Set default value for UseNuGetReferences -->
<PropertyGroup>
  <UseNuGetReferences Condition="'$(UseNuGetReferences)' == ''">false</UseNuGetReferences>
</PropertyGroup>

<!-- NuGet Package References for QA/UAT/PRD -->
<ItemGroup Condition="'$(UseNuGetReferences)' == 'true'">
  <PackageReference Include="LibraryB" Version="1.0.46" />
  <PackageReference Include="LibraryC" Version="1.0.46" />
</ItemGroup>

<!-- Project References for Local/DEV -->
<ItemGroup Condition="'$(UseNuGetReferences)' != 'true'">
  <ProjectReference Include="..\LibraryB\LibraryB.csproj" />
  <ProjectReference Include="..\LibraryC\LibraryC.csproj" />
</ItemGroup>
```

#### Workflow Example:
1. Developers work locally with project references
2. PR is created targeting QA branch
3. This action builds and publishes NuGet packages
4. QA deployment action uses `UseNuGetReferences=true`
5. QA environment tests the actual NuGet packages
6. Same packages progress through UAT to Production

This ensures:
- Consistent package versions across environments
- Proper testing of the exact packages going to production
- Easy debugging in development
- No version mismatches between environments

### Configuring Libraries

To configure your libraries, modify two sections in the workflow file:

1. **Path Triggers** - Define which library paths to monitor:
```yaml
on:
  pull_request:
    paths:
      - 'LibraryA/**'
      - 'LibraryB/**'
      - 'LibraryC/**'
      - 'LibraryD/**'
```

2. **Change Detection Filters** - Configure library dependencies:
```yaml
- name: Detect Changed Packages
  id: filter
  uses: dorny/paths-filter@v3
  with:
    filters: |
      "A:LibraryA/LibraryA.csproj:B+C":
        - 'LibraryA/**'
      "B:LibraryB/LibraryB.csproj:C":
        - 'LibraryB/**'
      "C:LibraryC/LibraryC.csproj:":
        - 'LibraryC/**'
      "D:LibraryD/LibraryD.nuspec:":
        - 'LibraryD/**'
```

The filter format is `"KEY:FILE_PATH:DEPENDENCIES"`:
- `KEY`: Single letter identifier for the library
- `FILE_PATH`: Path to the .csproj or .nuspec file
- `DEPENDENCIES`: Other library keys this library depends on (optional, use + to separate multiple dependencies)

Example: `"A:LibraryA/LibraryA.csproj:B+C"` means:
- Library identified as "A"
- Project file at "LibraryA/LibraryA.csproj"
- Depends on libraries B and C

### Version Updates

Version updates are controlled through PR comments using special tags:

- `[BREAKING_CHANGE:X]`: Increases major version (1.0.0 → 2.0.0)
- `[NEW_FEATURE:X]`: Increases minor version (1.0.0 → 1.1.0)
- No tag: Increases patch version (1.0.0 → 1.0.1)

Replace `X` with the library key (A, B, C, etc.).

Example PR comment:
```
[BREAKING_CHANGE:A] Major API changes in Library A
[NEW_FEATURE:B] Added new functionality to Library B
```

### Dependency Management

The action automatically:
1. Orders library builds based on dependencies
2. Updates dependent library references when a library version changes
3. Handles both project references and NuGet package references using the `UseNuGetReferences` property

### Output

The action adds a comment to the PR with:

#### Changes Summary
- List of changed libraries with their paths and dependencies
- File types (.csproj or .nuspec)

#### Version Changes
- All version updates made
- Both direct version changes and dependency updates

#### Created Tags
- Release tag (e.g., `Release.1.6.0`)
- Individual library tags (e.g., `LibraryA/v1.0.46`)

#### Package Information
- GitHub Packages URL
- NuGet source configuration details
- Authentication requirements

Example output:
```markdown
# Changes Summary

## Changed Libraries
* Library A
  * Path: `LibraryA/LibraryA.csproj`
  * Dependencies: B+C
  * File type: csproj

## Version Changes
* A: 1.0.45 -> 1.0.46
* B: Updated dependency A to 1.0.46

## Created Tags
* `Release.1.6.0`
* `LibraryA/v1.0.46`

## Package Information
* Package Registry: https://github.com/OWNER/REPO/packages
* NuGet Source: https://nuget.pkg.github.com/OWNER/index.json
* Required Authentication: GitHub Personal Access Token with `read:packages` scope
```

## Requirements

- GitHub repository with NuGet packages
- Libraries organized in separate directories
- Project files (.csproj) or NuGet specification files (.nuspec)
- GitHub Packages configured as the NuGet feed
- Visual Studio or .NET CLI with configured NuGet source

## Setup

1. Copy the workflow file to `.github/workflows/build.yml`
2. Update the path triggers and change detection filters for your libraries
3. Configure GitHub Packages access using `GITHUB_TOKEN`
4. Convert project references to conditional references using the template above
5. Configure your deployment workflows to use `UseNuGetReferences=true` in QA/UAT/PRD
6. Configure NuGet package source in Visual Studio and/or .NET CLI
7. Create a PAT with `read:packages` scope for package access

## Best Practices

1. Create Release branches from target branch to prevent merge conflicts that may interfere with the action execution (e.g., if action targets `qa`, create `Release.1.6.0` from `qa`)
2. Use consistent naming for library directories and project files
3. Document version changes in PR comments using the version tags (e.g., `[BREAKING_CHANGE:A] Removed deprecated methods`, `[NEW_FEATURE:B] Added async support`)
4. Maintain clear dependency chains in the change detection filters
5. Review the Changes Summary comment before merging PRs
6. Keep project references for local development
7. Use NuGet packages in QA and higher environments
8. Always test the exact package versions that will go to production
9. Store PAT securely and rotate regularly
10. Configure CI/CD systems with appropriate package source credentials

## Troubleshooting

### Missing Dependencies When Using UseNuGetReferences=true

When building with `UseNuGetReferences=true`, you might encounter errors about missing dependencies that weren't issues during local development. This typically happens with:
- Framework dependencies (e.g., System.ServiceProcess.ServiceController)
- Transitive dependencies (packages required by your dependencies)

This occurs because `UseNuGetReferences=true` changes how dependencies are resolved:
- With project references (`false`), dependencies are resolved through the project reference chain
- With package references (`true`), each project needs explicit package references

To fix this, add the missing dependencies to your .csproj files in the package references section:
```xml
<ItemGroup Condition="'$(UseNuGetReferences)' == 'true'">
  <!-- Existing package references -->
  <PackageReference Include="LibraryB" Version="1.0.0" />
  
  <!-- Framework and transitive dependencies -->
  <PackageReference Include="System.ServiceProcess.ServiceController" Version="8.0.0" />
  <PackageReference Include="Azure.Storage.Blobs" Version="12.19.1" />
</ItemGroup>
```

You can identify missing dependencies by:
1. Running the build locally with `UseNuGetReferences=true`
2. Checking build errors in the GitHub Action logs
3. Using `dotnet list package --include-transitive` to see all required packages

### Visual Studio NuGet Cache Issues

If Visual Studio gets stuck using an old package version even after a new version is published:

1. **Clear NuGet HTTP Cache**:
   ```powershell
   dotnet nuget locals http-cache --clear
   ```
   This command specifically clears the HTTP cache where NuGet stores the results of HTTP operations, which is usually the cause of stale package versions.

2. **Delete Visual Studio Cache**:
   - Close Visual Studio
   - Delete the following directories:
     ```
     %LocalAppData%\.nuget\packages
     %UserProfile%\.nuget\packages
     ```
   - Restart Visual Studio

3. **Force Package Restore**:
   - Right-click on solution in Solution Explorer
   - Select "Restore NuGet Packages"
   - Clean and rebuild solution

4. **Check Package Source**:
   - Tools > NuGet Package Manager > Package Manager Settings
   - Verify GitHub Packages source is properly configured and authenticated
   - Try moving it to the top of the source list

5. **Check Available Package Versions**:
   ```powershell
   dotnet nuget list source
   dotnet nuget list package PackageName
   ```
   This will show all configured sources and available versions of the package, helping identify if the package is visible and up to date.

These steps should resolve most caching issues with NuGet packages in Visual Studio.

## Adding a New Library

Here's an example of adding `LibraryE` that:
- Depends on `LibraryC`
- Is a dependency for `LibraryA`

### Option 1: Modern Project (.csproj)

1. Configure the project files:

```xml
<!-- LibraryE.csproj -->
<ItemGroup Condition="'$(UseNuGetReferences)' == 'true'">
  <PackageReference Include="LibraryC" Version="1.0.0" />
</ItemGroup>
<ItemGroup Condition="'$(UseNuGetReferences)' != 'true'">
  <ProjectReference Include="..\LibraryC\LibraryC.csproj" />
</ItemGroup>

<!-- LibraryA.csproj -->
<ItemGroup Condition="'$(UseNuGetReferences)' == 'true'">
  <PackageReference Include="LibraryE" Version="1.0.0" />
</ItemGroup>
<ItemGroup Condition="'$(UseNuGetReferences)' != 'true'">
  <ProjectReference Include="..\LibraryE\LibraryE.csproj" />
</ItemGroup>
```

### Option 2: Legacy Library (.nuspec)

1. Generate the initial nuspec file:
```powershell
nuget spec LibraryE
```
This creates a template `LibraryE.nuspec` that you can then modify:

```xml
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd">
  <metadata>
    <id>LibraryE</id>
    <version>1.0.0</version>
    <title>Library E</title>
    <authors>Your Name</authors>
    <description>Description of Library E</description>
    <dependencies>
      <dependency id="LibraryC" version="1.0.0" />
    </dependencies>
  </metadata>
  <files>
    <!-- Include compiled DLL from project output -->
    <file src="bin\Release\net8.0\LibraryE.dll" target="lib\net8.0" />
    <!-- Include XML documentation file if exists -->
    <file src="bin\Release\net8.0\LibraryE.xml" target="lib\net8.0" />
    <!-- Include PDB file for debugging -->
    <file src="bin\Release\net8.0\LibraryE.pdb" target="lib\net8.0" />
  </files>
</package>
```

2. Add the new library path to workflow triggers:
```yaml
on:
  pull_request:
    paths:
      - 'LibraryA/**'
      - 'LibraryB/**'
      - 'LibraryC/**'
      - 'LibraryD/**'
      - 'LibraryE/**'  # Add new library
```

3. Update the change detection filters:
```yaml
- name: Detect Changed Packages
  with:
    filters: |
      "C:LibraryC/LibraryC.csproj:":
        - 'LibraryC/**'
      "E:LibraryE/LibraryE.nuspec:C":  # E depends on C, using nuspec
        - 'LibraryE/**'
      "A:LibraryA/LibraryA.csproj:E":  # A depends on E
        - 'LibraryA/**'
      # ... other libraries ...
```

Now when:
- `LibraryC` changes → `LibraryE` updates its dependency → `LibraryA` updates its dependency
- `LibraryE` changes → `LibraryA` updates its dependency
- `LibraryA` changes → Only `LibraryA` version is updated