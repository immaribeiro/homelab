#!/usr/bin/env python3
"""Online, consistent daily backup of Hermes SQLite state databases.

For every state.db under /Users/imma/.hermes (root DB plus each profile
directory), an online snapshot is taken with the SQLite backup API (safe
for WAL-mode DBs that are actively being written by the gateway),
integrity-checked, and gzip-compressed to:

    /Users/imma/Backups/hermes/hermes-<profile>-YYYYMMDD.sqlite.gz

where <profile> is "main" for the root DB, otherwise the profile
directory name. Re-running on the same day overwrites the same dated file
(idempotent).

Stdlib only: sqlite3, gzip, argparse, pathlib (+ os, sys, tempfile).
"""

import argparse
import gzip
import os
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path

HERMES_HOME = Path("/Users/imma/.hermes")
BACKUP_DIR = Path("/Users/imma/Backups/hermes")
MAIN_PROFILE = "main"
CHUNK = 1024 * 1024  # 1 MiB


def discover_dbs(hermes_home):
    """Return [(db_path, profile_name), ...].

    Missing profile dirs and empty globs are handled gracefully: an
    absent profiles/ directory simply contributes nothing.
    """
    dbs = []
    root_db = hermes_home / "state.db"
    if root_db.is_file():
        dbs.append((root_db, MAIN_PROFILE))
    profiles_dir = hermes_home / "profiles"
    if profiles_dir.is_dir():
        for db in sorted(profiles_dir.glob("*/state.db")):
            if db.is_file():
                dbs.append((db, db.parent.name))
    return dbs


def snapshot_to(src, tmp_snap):
    """Copy src (read-only, WAL-safe) into tmp_snap via the backup API."""
    src_conn = sqlite3.connect(
        "file:{}?mode=ro".format(src), uri=True, timeout=30
    )
    try:
        snap_conn = sqlite3.connect(tmp_snap)
        try:
            src_conn.backup(snap_conn)
        finally:
            snap_conn.close()
    finally:
        src_conn.close()


def verify_integrity(src, tmp_snap):
    """Run PRAGMA integrity_check on the snapshot; raise on failure."""
    conn = sqlite3.connect(tmp_snap)
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    finally:
        conn.close()
    if not row or row[0] != "ok":
        raise RuntimeError(
            "integrity_check failed for {}: {!r}".format(src, row)
        )


def copy_stream(fin, fout):
    while True:
        chunk = fin.read(CHUNK)
        if not chunk:
            break
        fout.write(chunk)


def backup_one(src, profile, dest_dir, dry_run):
    """Back up one DB; prints progress. Raises on failure (non-dry-run)."""
    stamp = date.today().strftime("%Y%m%d")
    dest = dest_dir / "hermes-{}-{}.sqlite.gz".format(profile, stamp)
    if dry_run:
        print("would back up {} -> {}".format(src, dest))
        return

    dest_dir.mkdir(parents=True, exist_ok=True)

    fd, tmp_snap = tempfile.mkstemp(prefix="hermes-backup-", suffix=".snapshot.db")
    os.close(fd)
    try:
        snapshot_to(src, tmp_snap)
        verify_integrity(src, tmp_snap)

        fd_gz, tmp_gz = tempfile.mkstemp(
            prefix="hermes-backup-", suffix=".tmp.gz", dir=str(dest_dir)
        )
        os.close(fd_gz)
        try:
            with open(tmp_snap, "rb") as fin, gzip.open(
                tmp_gz, "wb", compresslevel=6
            ) as fout:
                copy_stream(fin, fout)
            os.replace(tmp_gz, str(dest))  # atomic, overwrites same-day file
        finally:
            if os.path.exists(tmp_gz):
                os.unlink(tmp_gz)

        print("backed up {} -> {} ({} bytes)".format(src, dest, dest.stat().st_size))
    finally:
        if os.path.exists(tmp_snap):
            os.unlink(tmp_snap)


def main():
    parser = argparse.ArgumentParser(
        description="Online consistent backup of Hermes state databases."
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="print what would be backed up without writing anything",
    )
    args = parser.parse_args()

    dbs = discover_dbs(HERMES_HOME)
    if not dbs:
        print("no state.db files found under {}".format(HERMES_HOME))
        return 0

    if args.dry_run:
        print("dry run: {} database(s) found".format(len(dbs)))
        for src, profile in dbs:
            backup_one(src, profile, BACKUP_DIR, dry_run=True)
        return 0

    errors = []
    for src, profile in dbs:
        try:
            backup_one(src, profile, BACKUP_DIR, dry_run=False)
        except Exception as exc:  # report and continue with the rest
            errors.append((src, exc))
            print("ERROR backing up {}: {}".format(src, exc), file=sys.stderr)

    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
