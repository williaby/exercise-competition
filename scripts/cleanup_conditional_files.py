#!/usr/bin/env python3
"""Clean up conditional files based on .cruft.json context.

This script reads the cookiecutter context from .cruft.json and removes
files that should not exist based on the feature flags configured during
project generation.

IMPORTANT: Run this script after `cruft update` to ensure conditional files
are properly removed. Cruft updates only sync file contents - it does NOT
re-run post-generation hooks that clean up conditional files.

Usage:
    python scripts/cleanup_conditional_files.py [--dry-run]

Options:
    --dry-run    Show what would be removed without actually removing

Example:
    # After running cruft update
    cruft update
    python scripts/cleanup_conditional_files.py

    # Preview what would be removed
    python scripts/cleanup_conditional_files.py --dry-run
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def get_cruft_context() -> dict[str, str]:
    """Read cookiecutter context from .cruft.json.

    Returns:
        Dictionary of cookiecutter context values.

    Raises:
        FileNotFoundError: If .cruft.json doesn't exist.
        json.JSONDecodeError: If .cruft.json is invalid JSON.
    """
    cruft_file = Path(".cruft.json")
    if not cruft_file.exists():
        msg = ".cruft.json not found. Is this a cruft-managed project?"
        raise FileNotFoundError(msg)

    cruft_data = json.loads(cruft_file.read_text())
    return cruft_data.get("context", {}).get("cookiecutter", {})


def remove_file(filepath: Path, dry_run: bool = False) -> bool:
    """Remove a file if it exists.

    Args:
        filepath: Path to the file to remove.
        dry_run: If True, only report what would be removed.

    Returns:
        True if file was removed (or would be), False if file didn't exist.
    """
    if filepath.exists():
        if dry_run:
            print(f"  [DRY RUN] Would remove: {filepath}")
        else:
            filepath.unlink()
            print(f"  ✓ Removed: {filepath}")
        return True
    return False


def remove_dir(dirpath: Path, dry_run: bool = False) -> bool:
    """Remove a directory if it exists.

    Args:
        dirpath: Path to the directory to remove.
        dry_run: If True, only report what would be removed.

    Returns:
        True if directory was removed (or would be), False if it didn't exist.
    """
    if dirpath.exists():
        if dry_run:
            print(f"  [DRY RUN] Would remove: {dirpath}/")
        else:
            shutil.rmtree(dirpath)
            print(f"  ✓ Removed: {dirpath}/")
        return True
    return False


def get_project_slug(context: dict) -> str:
    """Extract project_slug from context.

    Args:
        context: Cookiecutter context dictionary.

    Returns:
        Project slug string.
    """
    return context.get("project_slug", "")


def _remove_paths(paths: list[tuple[Path, bool]], dry_run: bool) -> int:
    """Remove a list of files and directories.

    Args:
        paths: List of (path, is_directory) tuples.
        dry_run: If True, only report what would be removed.

    Returns:
        Number of items removed.
    """
    count = 0
    for path, is_dir in paths:
        remover = remove_dir if is_dir else remove_file
        if remover(path, dry_run):
            count += 1
    return count


def _cleanup_simple_features(context: dict, dry_run: bool) -> int:
    """Clean up features that map to a single file removal."""
    simple_features: list[tuple[str, Path]] = [
        ("include_cli", Path("__SRC__/cli.py")),  # placeholder, handled in caller
        ("include_nox", Path("noxfile.py")),
        ("use_pre_commit", Path(".pre-commit-config.yaml")),
        ("include_code_of_conduct", Path("CODE_OF_CONDUCT.md")),
        ("include_security_policy", Path("SECURITY.md")),
        ("include_contributing_guide", Path("CONTRIBUTING.md")),
        ("include_renovate", Path("renovate.json")),
        ("include_coderabbit", Path(".coderabbit.yaml")),
        ("include_semantic_release", Path(".github/workflows/release.yml")),
    ]
    count = 0
    for feature_key, filepath in simple_features:
        if context.get(feature_key) == "no" and remove_file(filepath, dry_run):
            count += 1
    return count


def _cleanup_mkdocs(dry_run: bool) -> int:
    """Clean up MkDocs-related files and directories."""
    paths: list[tuple[Path, bool]] = [
        (Path("mkdocs.yml"), False),
        (Path("docs"), True),
        (Path("tools/validate_front_matter.py"), False),
        (Path("tools/frontmatter_contract"), True),
        (Path(".github/workflows/docs.yml"), False),
    ]
    return _remove_paths(paths, dry_run)


def _cleanup_codecov(dry_run: bool) -> int:
    """Clean up Codecov-related files."""
    paths: list[tuple[Path, bool]] = [
        (Path("codecov.yml"), False),
        (Path(".github/workflows/codecov.yml"), False),
    ]
    return _remove_paths(paths, dry_run)


def _cleanup_sonarcloud(dry_run: bool) -> int:
    """Clean up SonarCloud-related files."""
    paths: list[tuple[Path, bool]] = [
        (Path("sonar-project.properties"), False),
        (Path(".github/workflows/sonarcloud.yml"), False),
    ]
    return _remove_paths(paths, dry_run)


def _cleanup_reuse_licensing(dry_run: bool) -> int:
    """Clean up REUSE licensing files."""
    paths: list[tuple[Path, bool]] = [
        (Path("REUSE.toml"), False),
        (Path("LICENSES"), True),
        (Path(".github/workflows/reuse.yml"), False),
    ]
    return _remove_paths(paths, dry_run)


def _cleanup_docker(dry_run: bool) -> int:
    """Clean up Docker-related files."""
    paths: list[tuple[Path, bool]] = [
        (Path("Dockerfile"), False),
        (Path("docker-compose.yml"), False),
        (Path("docker-compose.prod.yml"), False),
        (Path(".dockerignore"), False),
        (Path(".github/workflows/container-security.yml"), False),
    ]
    return _remove_paths(paths, dry_run)


def _cleanup_api_framework(src_dir: Path, dry_run: bool) -> int:
    """Clean up API framework files and empty middleware directory."""
    paths: list[tuple[Path, bool]] = [
        (src_dir / "api", True),
        (src_dir / "middleware" / "security.py", False),
        (src_dir / "middleware" / "correlation.py", False),
    ]
    count = _remove_paths(paths, dry_run)

    # Remove middleware dir if empty (only __pycache__ and __init__.py remain)
    middleware_dir = src_dir / "middleware"
    if middleware_dir.exists() and not any(
        f
        for f in middleware_dir.iterdir()
        if f.name not in ("__pycache__", "__init__.py")
    ):
        if remove_dir(middleware_dir, dry_run):
            count += 1
    return count


def _cleanup_fuzzing(dry_run: bool) -> int:
    """Clean up fuzzing-related files and directories."""
    paths: list[tuple[Path, bool]] = [
        (Path(".github/workflows/cifuzzy.yml"), False),
        (Path(".clusterfuzzlite"), True),
        (Path("fuzz"), True),
    ]
    return _remove_paths(paths, dry_run)


def cleanup_conditional_files(context: dict, dry_run: bool = False) -> int:
    """Remove files based on cookiecutter context settings.

    Args:
        context: Cookiecutter context from .cruft.json.
        dry_run: If True, only report what would be removed.

    Returns:
        Number of files/directories removed.
    """
    project_slug = get_project_slug(context)
    if not project_slug:
        print("❌ Could not determine project_slug from .cruft.json")
        return 0

    src_dir = Path(f"src/{project_slug}")
    removed_count = 0

    print("\n🧹 Cleaning up conditional files...")

    # CLI (src-relative, handled separately from simple_features)
    if context.get("include_cli") == "no" and remove_file(src_dir / "cli.py", dry_run):
        removed_count += 1

    # Multi-file feature cleanups
    if context.get("use_mkdocs") == "no":
        removed_count += _cleanup_mkdocs(dry_run)

    # Simple single-file features (excluding CLI which needs src_dir)
    simple_features: list[tuple[str, Path]] = [
        ("include_nox", Path("noxfile.py")),
        ("use_pre_commit", Path(".pre-commit-config.yaml")),
        ("include_code_of_conduct", Path("CODE_OF_CONDUCT.md")),
        ("include_security_policy", Path("SECURITY.md")),
        ("include_contributing_guide", Path("CONTRIBUTING.md")),
        ("include_renovate", Path("renovate.json")),
        ("include_coderabbit", Path(".coderabbit.yaml")),
        ("include_semantic_release", Path(".github/workflows/release.yml")),
    ]
    for feature_key, filepath in simple_features:
        if context.get(feature_key) == "no" and remove_file(filepath, dry_run):
            removed_count += 1

    if context.get("include_codecov") == "no":
        removed_count += _cleanup_codecov(dry_run)

    if context.get("include_sonarcloud") == "no":
        removed_count += _cleanup_sonarcloud(dry_run)

    if context.get("use_reuse_licensing") == "no":
        removed_count += _cleanup_reuse_licensing(dry_run)

    if context.get("include_docker") == "no":
        removed_count += _cleanup_docker(dry_run)

    # API Framework / Health Checks
    if context.get("include_api_framework") == "no":
        removed_count += _cleanup_api_framework(src_dir, dry_run)
    elif context.get("include_health_checks") == "no" and remove_file(
        src_dir / "api" / "health.py", dry_run
    ):
        removed_count += 1

    # Src-relative single-file features
    if context.get("include_sentry") == "no" and remove_file(
        src_dir / "core" / "sentry.py", dry_run
    ):
        removed_count += 1

    if context.get("include_background_jobs") == "no" and remove_dir(
        src_dir / "jobs", dry_run
    ):
        removed_count += 1

    if context.get("include_caching") == "no" and remove_file(
        src_dir / "core" / "cache.py", dry_run
    ):
        removed_count += 1

    if context.get("include_load_testing") == "no" and remove_dir(
        Path("tests/load"), dry_run
    ):
        removed_count += 1

    if context.get("include_fuzzing") == "no":
        removed_count += _cleanup_fuzzing(dry_run)

    if context.get("include_github_actions") == "no" and remove_dir(
        Path(".github"), dry_run
    ):
        removed_count += 1

    return removed_count


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("🔍 Running in dry-run mode (no files will be removed)")

    try:
        context = get_cruft_context()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in .cruft.json: {e}")
        return 1

    removed_count = cleanup_conditional_files(context, dry_run)

    if removed_count > 0:
        action = "would be removed" if dry_run else "removed"
        print(f"\n✅ {removed_count} file(s)/directory(ies) {action}")
    else:
        print("\n✅ No orphaned files found - project is clean!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
