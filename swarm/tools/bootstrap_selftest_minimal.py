#!/usr/bin/env python3
"""
Bootstrap a new project with selftest-minimal template.

Usage:
    uv run swarm/tools/bootstrap_selftest_minimal.py /path/to/new/repo
    uv run swarm/tools/bootstrap_selftest_minimal.py /path/to/new/repo --init-git
    uv run swarm/tools/bootstrap_selftest_minimal.py /path/to/new/repo --install-deps

This script copies the selftest-minimal template to a target directory,
optionally initializing git and installing dependencies.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Template location relative to this script
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TEMPLATE_DIR = REPO_ROOT / "templates" / "selftest-minimal"

# Files to copy from template (excluding old selftest/ subdir)
TEMPLATE_FILES = [
    "selftest.yaml",
    "pyproject.toml",
    "README.md",
    ".github/workflows/selftest.yml",
]


def copy_template(target: Path, overwrite: bool = False) -> list[str]:
    """
    Copy template files to target directory.

    Args:
        target: Target directory path
        overwrite: If True, overwrite existing files

    Returns:
        List of copied file paths (relative to target)
    """
    copied = []

    for rel_path in TEMPLATE_FILES:
        src = TEMPLATE_DIR / rel_path
        dst = target / rel_path

        if not src.exists():
            print(f"Warning: Template file not found: {src}", file=sys.stderr)
            continue

        if dst.exists() and not overwrite:
            print(f"Skipping (exists): {rel_path}")
            continue

        # Create parent directories
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(src, dst)
        copied.append(rel_path)
        print(f"Copied: {rel_path}")

    return copied


def init_git(target: Path) -> bool:
    """Initialize git repository if not already initialized."""
    git_dir = target / ".git"
    if git_dir.exists():
        print("Git repository already initialized")
        return True

    result = subprocess.run(
        ["git", "init"],
        cwd=target,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("Initialized git repository")
        return True
    else:
        print(f"Failed to initialize git: {result.stderr}", file=sys.stderr)
        return False


def install_deps(target: Path) -> bool:
    """Install dependencies using uv."""
    result = subprocess.run(
        ["uv", "sync"],
        cwd=target,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("Dependencies installed")
        return True
    else:
        # Try pip as fallback
        result = subprocess.run(
            ["pip", "install", "-e", "."],
            cwd=target,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Dependencies installed (via pip)")
            return True
        print(f"Failed to install dependencies: {result.stderr}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap a new project with selftest-minimal template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Copy template to new directory
    %(prog)s /path/to/new/repo

    # Copy template and initialize git
    %(prog)s /path/to/new/repo --init-git

    # Copy template and install dependencies
    %(prog)s /path/to/new/repo --install-deps

    # Full setup
    %(prog)s /path/to/new/repo --init-git --install-deps
""",
    )

    parser.add_argument(
        "target",
        type=Path,
        help="Target directory for the new project",
    )
    parser.add_argument(
        "--init-git",
        action="store_true",
        help="Initialize git repository in target",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies after copying",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without actually copying",
    )

    args = parser.parse_args()
    target = args.target.resolve()

    # Verify template exists
    if not TEMPLATE_DIR.exists():
        print(f"Error: Template directory not found: {TEMPLATE_DIR}", file=sys.stderr)
        return 2

    # Create target directory
    if args.dry_run:
        print(f"Would create: {target}")
        print("Would copy:")
        for f in TEMPLATE_FILES:
            src = TEMPLATE_DIR / f
            if src.exists():
                print(f"  {f}")
        return 0

    target.mkdir(parents=True, exist_ok=True)

    print(f"Bootstrapping selftest-minimal to: {target}")
    print()

    # Copy template files
    copied = copy_template(target, overwrite=args.overwrite)

    if not copied:
        print("No files copied (all exist or template missing)")
        return 1

    print(f"\nCopied {len(copied)} files")

    # Optional: init git
    if args.init_git:
        print()
        init_git(target)

    # Optional: install deps
    if args.install_deps:
        print()
        install_deps(target)

    print()
    print("Next steps:")
    print(f"  cd {target}")
    print("  # Edit selftest.yaml to match your project")
    print("  selftest run  # Run selftest")

    return 0


if __name__ == "__main__":
    sys.exit(main())
