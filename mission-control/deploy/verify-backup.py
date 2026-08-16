#!/usr/bin/env python3
"""Verify hermes backups: decompress each .sqlite.gz to a temp path,
run PRAGMA integrity_check, then delete the temp (TemporaryDirectory)."""
import gzip
import os
import sqlite3
import tempfile
from pathlib import Path

backup_dir = Path("/Users/imma/Backups/hermes")
with tempfile.TemporaryDirectory(prefix="hermes-verify-") as tmp:
    for gz in sorted(backup_dir.glob("*.sqlite.gz")):
        out = os.path.join(tmp, gz.stem)  # gz.stem strips the .gz suffix
        with gzip.open(gz, "rb") as fin, open(out, "wb") as fout:
            while True:
                chunk = fin.read(1024 * 1024)
                if not chunk:
                    break
                fout.write(chunk)
        conn = sqlite3.connect(out)
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        print(
            "integrity_check(%s): %s  (decompressed %d bytes)"
            % (gz.name, result, os.path.getsize(out))
        )
print("temp cleaned (TemporaryDirectory)")
