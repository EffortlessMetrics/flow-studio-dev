#!/usr/bin/env python3
"""
Migrate selftest_degradations.log from v1.0 to v1.1 schema.

Schema v1.1 adds two required fields:
  - status: StepStatus enum (PASS, FAIL, SKIP, TIMEOUT)
  - reason: Why the step ended in that status

v1.0 only logged failures, so we can safely default:
  - status = "FAIL"
  - reason = "nonzero_exit"

Usage:
    # Preview migration (dry-run)
    uv run swarm/tools/selftest_migrate_logs.py

    # Apply migration (creates backup)
    uv run swarm/tools/selftest_migrate_logs.py --apply

    # Migrate specific file
    uv run swarm/tools/selftest_migrate_logs.py --file /path/to/log.jsonl --apply
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Default log path
DEFAULT_LOG_PATH = Path(__file__).resolve().parents[2] / "selftest_degradations.log"


def migrate_entry(entry: dict) -> dict:
    """
    Migrate a single log entry from v1.0 to v1.1 schema.

    Args:
        entry: Original log entry dict

    Returns:
        Migrated entry with status and reason fields
    """
    # If already has status and reason, return as-is
    if "status" in entry and "reason" in entry:
        return entry

    # v1.0 only logged failures, so these are safe defaults
    migrated = entry.copy()
    if "status" not in migrated:
        migrated["status"] = "FAIL"
    if "reason" not in migrated:
        migrated["reason"] = "nonzero_exit"

    return migrated


def migrate_log_file(path: Path, apply: bool = False) -> tuple[int, int, int]:
    """
    Migrate a log file from v1.0 to v1.1 schema.

    Args:
        path: Path to the log file
        apply: If True, write changes and create backup. If False, dry-run only.

    Returns:
        Tuple of (total_entries, migrated_count, already_v11_count)
    """
    if not path.exists():
        print(f"Log file not found: {path}")
        return (0, 0, 0)

    content = path.read_text()
    lines = content.strip().split("\n") if content.strip() else []

    if not lines:
        print(f"Log file is empty: {path}")
        return (0, 0, 0)

    migrated_lines = []
    migrated_count = 0
    already_v11_count = 0
    errors = []

    for i, line in enumerate(lines, 1):
        if not line.strip():
            migrated_lines.append("")
            continue

        try:
            entry = json.loads(line)
            was_v10 = "status" not in entry or "reason" not in entry
            migrated = migrate_entry(entry)
            migrated_lines.append(json.dumps(migrated))

            if was_v10:
                migrated_count += 1
            else:
                already_v11_count += 1
        except json.JSONDecodeError as e:
            errors.append(f"Line {i}: Invalid JSON - {e}")
            migrated_lines.append(line)  # Keep original on error

    total = migrated_count + already_v11_count

    print(f"\nMigration summary for {path}:")
    print(f"  Total entries:    {total}")
    print(f"  Already v1.1:     {already_v11_count}")
    print(f"  Migrated to v1.1: {migrated_count}")

    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for err in errors[:5]:
            print(f"    - {err}")
        if len(errors) > 5:
            print(f"    ... and {len(errors) - 5} more")

    if apply and migrated_count > 0:
        # Create backup
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = path.with_suffix(f".v1.0.bak-{timestamp}")
        backup_path.write_text(content)
        print(f"\n  Backup created: {backup_path}")

        # Write migrated content
        path.write_text("\n".join(migrated_lines) + "\n")
        print(f"  Migration applied: {path}")
    elif apply and migrated_count == 0:
        print("\n  No migration needed (all entries already v1.1)")
    else:
        print("\n  Dry-run mode. Use --apply to write changes.")

    return (total, migrated_count, already_v11_count)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate selftest_degradations.log from v1.0 to v1.1 schema"
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help=f"Path to log file (default: {DEFAULT_LOG_PATH})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply migration (creates backup). Without this flag, runs in dry-run mode.",
    )
    args = parser.parse_args()

    print("Selftest Degradation Log Migration (v1.0 → v1.1)")
    print("=" * 50)

    total, migrated, already = migrate_log_file(args.file, args.apply)

    if migrated > 0 and not args.apply:
        print("\nTo apply migration, run:")
        print("  uv run swarm/tools/selftest_migrate_logs.py --apply")
        sys.exit(0)

    sys.exit(0 if total >= 0 else 1)


if __name__ == "__main__":
    main()
