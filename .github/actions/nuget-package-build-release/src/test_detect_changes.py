import unittest
import json
import os
from detect_changes import detect_changes, matches_pattern

class TestDetectChanges(unittest.TestCase):
    def setUp(self):
        # Sample project configuration
        self.projects = {
            "LibraryA": {
                "path": "LibraryA/LibraryA.csproj",
                "patterns": ["LibraryA/**"],
                "dependencies": ["LibraryB", "LibraryC"]
            },
            "LibraryB": {
                "path": "LibraryB/LibraryB.csproj",
                "patterns": ["LibraryB/**"],
                "dependencies": ["LibraryC"]
            },
            "LibraryC": {
                "path": "LibraryC/LibraryC.csproj",
                "patterns": ["LibraryC/**"],
                "dependencies": []
            },
            "LibraryD": {
                "path": "LibraryD/LibraryD.nuspec",
                "patterns": ["LibraryD/**"],
                "dependencies": []
            }
        }

    def test_matches_pattern(self):
        """Test pattern matching functionality"""
        # Test basic pattern matching
        self.assertTrue(matches_pattern("LibraryA/file.cs", ["LibraryA/**"]))
        self.assertTrue(matches_pattern("LibraryA/src/file.cs", ["LibraryA/**"]))
        self.assertFalse(matches_pattern("LibraryB/file.cs", ["LibraryA/**"]))
        
        # Test multiple patterns
        self.assertTrue(matches_pattern("LibraryA/file.cs", ["LibraryA/**", "*.cs"]))
        self.assertTrue(matches_pattern("src/file.cs", ["src/**", "*.cs"]))
        
        # Test exact matches
        self.assertTrue(matches_pattern("file.cs", ["file.cs"]))
        self.assertFalse(matches_pattern("file.txt", ["file.cs"]))

    def test_detect_single_project_change(self):
        """Test changes in a single project"""
        changed_files = ["LibraryA/file.cs"]
        _, modified_packages, _, has_nuspec = detect_changes(self.projects, changed_files)
        self.assertEqual(modified_packages, {"X1"})  # LibraryA is mapped to X1
        self.assertFalse(has_nuspec)

    def test_detect_multiple_project_changes(self):
        """Test changes in multiple projects"""
        changed_files = ["LibraryA/file.cs", "LibraryB/file.cs"]
        _, modified_packages, _, has_nuspec = detect_changes(self.projects, changed_files)
        self.assertEqual(modified_packages, {"X1", "X2"})  # LibraryA->X1, LibraryB->X2
        self.assertFalse(has_nuspec)

    def test_detect_nuspec_changes(self):
        """Test changes in a project with nuspec file"""
        changed_files = ["LibraryD/file.cs"]
        _, modified_packages, _, has_nuspec = detect_changes(self.projects, changed_files)
        self.assertEqual(modified_packages, {"X4"})  # LibraryD is mapped to X4
        self.assertTrue(has_nuspec)

    def test_no_changes(self):
        """Test when no changes match any project"""
        changed_files = ["unrelated/file.cs"]
        _, modified_packages, _, has_nuspec = detect_changes(self.projects, changed_files)
        self.assertEqual(modified_packages, set())
        self.assertFalse(has_nuspec)

    def test_nested_path_changes(self):
        """Test changes in nested paths"""
        changed_files = ["LibraryA/src/subfolder/file.cs"]
        _, modified_packages, _, has_nuspec = detect_changes(self.projects, changed_files)
        self.assertEqual(modified_packages, {"X1"})
        self.assertFalse(has_nuspec)

    def test_multiple_patterns_per_project(self):
        """Test project with multiple patterns"""
        # Add a project with multiple patterns
        self.projects["LibraryE"] = {
            "path": "LibraryE/LibraryE.csproj",
            "patterns": ["LibraryE/**", "shared/**", "*.shared.cs"],
            "dependencies": []
        }
        
        test_cases = [
            (["LibraryE/file.cs"], {"X5"}),
            (["shared/file.cs"], {"X5"}),
            (["any/file.shared.cs"], {"X5"}),
            (["unrelated/file.cs"], set())
        ]
        
        for changed_files, expected in test_cases:
            _, modified_packages, _, _ = detect_changes(self.projects, changed_files)
            self.assertEqual(modified_packages, expected)

    def test_github_event_detection(self):
        """Test detection using GitHub event data"""
        event = {
            "repository": {
                "full_name": "vmh32/GitHub-Action-Test"
            },
            "before": "abc123",
            "after": "def456"
        }
        _, modified_packages, _, has_nuspec = detect_changes(self.projects, event)
        self.assertEqual(modified_packages, {"X1", "X2"})  # Should match default test files
        self.assertFalse(has_nuspec)

if __name__ == '__main__':
    unittest.main() 