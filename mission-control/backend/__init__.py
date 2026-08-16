"""Hermes Mission Control — read-only observability layer.

Reads all Hermes profile state databases (SQLite, WAL mode) and exposes a
unified, aggregated view of every session across every agent/profile and
interface (CLI, Telegram, desktop, cron, ...).

SAFETY CONTRACT: this package never writes to Hermes state. Every database
connection is opened with `mode=ro`. No Hermes files are ever modified.
"""
__version__ = "0.1.0"
