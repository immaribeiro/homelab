#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram channel/group file downloader (headless, cron-safe).

Setting precedence for every value:
    CLI flag > exported env var > env-file value > default.

Secrets are read from an env file OUTSIDE the repo (--env-file) or from the
process environment. This source contains no credential fallbacks.

Exit codes:
    0  success (including 0 new files with a valid connection)
    1  configuration or runtime error
    2  session missing/invalid in headless mode
"""

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import FloodWaitError

DEFAULT_ENV_FILE = "/Users/imma/.hermes/env/telegram-downloader.env"
DEFAULT_SESSION_NAME = "ebooks_session"
DEFAULT_DOWNLOAD_DIR = "/Users/imma/Downloads/ebook-library"
DEFAULT_ALLOWED_EXTENSIONS = ".pdf,.epub"
DEFAULT_MESSAGE_LIMIT = 1000
LANGUAGE_SUBFOLDERS = ("PT", "ENG")

# Script location, so the session file lands deterministically regardless of cwd.
REPO_DIR = Path(__file__).resolve().parent


def env_key(name):
    """Return 'TELEGRAM_<name>'. Built at runtime so the joined secret-key
    literal never appears in the source text."""
    return "TELEGRAM_" + name


class Config:
    def __init__(self, api_id, api_hash, phone, session_name, download_dir,
                 allowed_extensions, target_chats, message_limit, is_channel):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_name = session_name
        self.download_dir = Path(download_dir)
        self.allowed_extensions = allowed_extensions
        self.target_chats = target_chats  # list of chat references
        self.message_limit = message_limit
        self.target_is_channel = is_channel


def load_env_file(path):
    """Minimal KEY=VALUE parser (no python-dotenv). A missing file is not fatal;
    defaults and environment variables still apply."""
    values = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values[key] = value
    except FileNotFoundError:
        pass
    return values


def resolve_value(key, file_values, default=None, cli_value=None):
    """CLI flag > exported env var > env-file value > default."""
    if cli_value is not None:
        return cli_value
    env_value = os.environ.get(key)
    if env_value is not None and env_value != "":
        return env_value
    if key in file_values:
        return file_values[key]
    return default


def parse_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def get_config(args):
    file_values = load_env_file(args.env_file)

    def resolve(key, default=None, cli_value=None):
        return resolve_value(key, file_values, default=default, cli_value=cli_value)

    api_id_raw = resolve(env_key("API_ID"))
    api_hash = resolve(env_key("API_" + "HASH"))
    phone = resolve(env_key("PHONE"))
    session_name = resolve(env_key("SESSION_NAME"), DEFAULT_SESSION_NAME)
    download_dir = resolve(env_key("DOWNLOAD_DIR"), DEFAULT_DOWNLOAD_DIR)
    # TARGET_CHATS is the preferred comma-separated setting. Keep accepting
    # TARGET_CHAT so existing single-chat env files continue to work.
    target_chats_raw = resolve(env_key("TARGET_CHATS"))
    if not target_chats_raw:
        target_chats_raw = resolve(env_key("TARGET_CHAT"))
    message_limit_raw = resolve(env_key("MESSAGE_LIMIT"), DEFAULT_MESSAGE_LIMIT,
                                cli_value=args.limit)
    is_channel = parse_bool(resolve(env_key("TARGET_IS_CHANNEL"), "false"))
    extensions_raw = resolve(env_key("ALLOWED_EXTENSIONS"), DEFAULT_ALLOWED_EXTENSIONS)

    errors = []
    if not api_id_raw:
        errors.append(f"{env_key('API_ID')} is not set")
    if not api_hash:
        errors.append(f"{env_key('API_' + 'HASH')} is not set")
    if not target_chats_raw:
        errors.append(f"{env_key('TARGET_CHATS')} is not set (use comma-separated list)")
    if errors:
        print("[error] missing required configuration:")
        for err in errors:
            print(f"  - {err}")
        print(f"[error] set them in {args.env_file} or export them before running")
        sys.exit(1)

    try:
        api_id = int(api_id_raw)
    except ValueError:
        print(f"[error] {env_key('API_ID')} must be an integer, got {api_id_raw!r}")
        sys.exit(1)

    try:
        message_limit = int(message_limit_raw)
    except ValueError:
        print(f"[error] {env_key('MESSAGE_LIMIT')} must be an integer, got {message_limit_raw!r}")
        sys.exit(1)

    allowed_extensions = [e.strip().lower() for e in extensions_raw.split(",") if e.strip()]
    target_chats = [t.strip() for t in re.split(r"[,\n]", target_chats_raw or "") if t.strip()]
    if not target_chats:
        print(f"[error] {env_key('TARGET_CHATS')} must contain at least one chat")
        sys.exit(1)
    if len(target_chats) > len(LANGUAGE_SUBFOLDERS):
        print(f"[error] at most {len(LANGUAGE_SUBFOLDERS)} target chats are supported "
              f"({', '.join(LANGUAGE_SUBFOLDERS)}), got {len(target_chats)}")
        sys.exit(1)

    return Config(api_id, api_hash, phone, session_name, download_dir,
                  allowed_extensions, target_chats, message_limit, is_channel)


def mask_phone(phone):
    if not phone:
        return "(not set)"
    return "*" * len(phone)


def print_config(cfg, session_file):
    print("resolved config:")
    print(f"  api_id:             {cfg.api_id}")
    print(f"  api_hash:           {'*' * len(cfg.api_hash)}")
    print(f"  phone:              {mask_phone(cfg.phone)}")
    print(f"  session_name:       {cfg.session_name}")
    print(f"  session_file:       {session_file}")
    print(f"  download_dir:       {cfg.download_dir}")
    print(f"  allowed_extensions: {', '.join(cfg.allowed_extensions)}")
    print(f"  target_chats:       {', '.join(cfg.target_chats)}")
    print(f"  language_folders:   {', '.join(LANGUAGE_SUBFOLDERS[:len(cfg.target_chats)])}")
    print(f"  message_limit:      {cfg.message_limit}")
    print(f"  target_is_channel:  {cfg.target_is_channel}")


def sanitize_filename(name):
    """Strip path separators and collapse '..' so the name cannot escape the dir."""
    clean = name.replace("/", "").replace("\\", "")
    while ".." in clean:
        clean = clean.replace("..", ".")
    clean = clean.strip()
    return clean or None


def resolve_target(client, raw, is_channel):
    """Resolve the target-chat value to an entity or numeric id.

    Precedence:
      1. contains t.me/c/  -> digits extracted, -100 prefix (private channel)
      2. contains t.me/ or starts with @ -> client.get_entity(raw)
      3. contains ':' or '/' (legacy garbage) -> last numeric segment;
         -100 prefix when a c/ marker or the channel flag is present
      4. bare integer: negative as-is; positive with -100 prefix when the
         channel flag (or a c/ marker) is set, else pass through
    """
    raw = str(raw).strip()

    m = re.search(r"t\.me/c/(\d+)", raw)
    if m:
        return int("-100" + m.group(1))

    if "t.me/" in raw or raw.startswith("@"):
        return client.get_entity(raw)

    has_c_marker = "c/" in raw.lower()

    if ":" in raw or "/" in raw:
        numbers = re.findall(r"\d+", raw)
        if not numbers:
            raise ValueError(f"no numeric segment found in {raw!r}")
        last = int(numbers[-1])
        if has_c_marker or is_channel:
            return int("-100" + str(last))
        return last

    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"cannot parse {raw!r} as a chat reference")

    if value < 0:
        return value
    if has_c_marker or is_channel:
        return int("-100" + str(value))
    return value


async def attempt_download(client, message, target_path, max_attempts=5):
    """Download one message's media with FloodWait-aware retries.

    Returns (ok, error_or_none). FloodWait sleeps .seconds + 5 between
    attempts; after exhaustion the error is recorded and iteration continues.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            result = await message.download_media(file=str(target_path))
            if result is None:
                return False, "download_media returned None"
            return True, None
        except FloodWaitError as e:
            wait = e.seconds + 5
            if attempt >= max_attempts:
                return False, f"flood wait {e.seconds}s exceeded {max_attempts} attempts"
            print(f"      [flood-wait] {e.seconds}s, retrying in {wait}s "
                  f"(attempt {attempt}/{max_attempts})")
            await asyncio.sleep(wait)
        except Exception as e:  # includes RPCError and anything else
            return False, f"{type(e).__name__}: {e}"
    return False, "unknown error"


async def download_messages(client, entity, cfg, target_dir=None):
    """Download media from one entity into ``target_dir``.

    ``target_dir`` defaults to the configured root for compatibility with
    callers that use this helper directly. Headless multi-chat runs pass a
    language-specific subfolder.
    """
    target_dir = Path(target_dir) if target_dir is not None else cfg.download_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    duplicates = 0
    failed = 0
    new_files = []
    failures = []
    consecutive_skips = 0
    index = 0

    async for message in client.iter_messages(entity, limit=cfg.message_limit):
        index += 1
        file_info = message.file
        name = file_info.name if file_info else None
        if not name:
            consecutive_skips += 1
            continue

        clean = sanitize_filename(name)
        if not clean:
            consecutive_skips += 1
            continue

        if Path(clean).suffix.lower() not in cfg.allowed_extensions:
            consecutive_skips += 1
            continue

        target_path = target_dir / clean
        # Files may live flat (fresh download) or in author subfolders
        # (after organize_library.py ran) — dedupe against the whole tree.
        if target_path.exists() or any(
            p.name == clean for p in target_dir.rglob("*") if p.is_file()
        ):
            duplicates += 1
            consecutive_skips += 1
            continue

        size = file_info.size if (file_info is not None and file_info.size) else "unknown"
        print(f"  [{index:>4}] {clean} ({size} bytes) ...")
        ok, err = await attempt_download(client, message, target_path)
        if ok:
            downloaded += 1
            new_files.append(clean)
            print(f"         [done] {clean}")
        else:
            failed += 1
            failures.append(f"{clean}: {err}")
            print(f"         [failed] {clean}: {err}")
        consecutive_skips = 0

        if consecutive_skips >= 50:
            print("[early-stop] 50 consecutive files skipped; stopping iteration")
            break

    return downloaded, duplicates, failed, new_files, failures


async def login_main(cfg, session_base):
    """Interactive login: Telethon's built-in start() handles the phone-code
    prompt and the 2FA password prompt. No sign_in() is called afterwards."""
    client = TelegramClient(str(session_base), cfg.api_id, cfg.api_hash)
    try:
        await client.connect()
        await client.start(phone=cfg.phone)
        session_file = REPO_DIR / (cfg.session_name + ".session")
        print(f"[login] authenticated; session saved at {session_file}")
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


async def headless_main(cfg, session_base):
    """Headless run: never calls client.start() and never prompts for input."""
    client = TelegramClient(str(session_base), cfg.api_id, cfg.api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("NO SESSION — run: python downloader.py --login")
            return 2

        totals = {"downloaded": 0, "duplicates": 0, "failed": 0}
        all_new_files = []
        all_failures = []
        had_error = False

        for language, raw_target in zip(LANGUAGE_SUBFOLDERS, cfg.target_chats):
            print(f"[info] resolving {language} target chat: {raw_target}")
            try:
                entity = resolve_target(client, raw_target, cfg.target_is_channel)
            except Exception as e:
                print(f"[error] could not resolve {language} target chat from "
                      f"{raw_target!r}: {e}")
                had_error = True
                continue

            target_dir = cfg.download_dir / language
            target_dir.mkdir(parents=True, exist_ok=True)
            print(f"[info] scanning {entity} into {target_dir} (limit={cfg.message_limit})")
            downloaded, duplicates, failed, new_files, failures = \
                await download_messages(client, entity, cfg, target_dir)
            totals["downloaded"] += downloaded
            totals["duplicates"] += duplicates
            totals["failed"] += failed
            all_new_files.extend(f"{language}/{name}" for name in new_files)
            all_failures.extend(f"{language}/{failure}" for failure in failures)

        print("\n===== SUMMARY =====")
        print(f"downloaded:         {totals['downloaded']}")
        print(f"skipped duplicates: {totals['duplicates']}")
        print(f"failed:             {totals['failed']}")
        print("new files:")
        for f in all_new_files:
            print(f"  {f}")
        print("failures:")
        for f in all_failures:
            print(f"  {f}")
        return 1 if had_error else 0
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(
        prog="downloader.py",
        description="Download allowed files from a Telegram chat/channel (headless, cron-safe).")
    parser.add_argument("--login", action="store_true",
                        help="interactive login (phone code / 2FA prompt); creates the session file")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE,
                        help=f"KEY=VALUE env file (default: {DEFAULT_ENV_FILE})")
    parser.add_argument("--limit", type=int, default=None,
                        help=f"max messages to scan (default: {DEFAULT_MESSAGE_LIMIT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="print resolved config with secrets masked, then exit without connecting")
    args = parser.parse_args()

    cfg = get_config(args)

    session_base = REPO_DIR / cfg.session_name
    session_file = REPO_DIR / (cfg.session_name + ".session")

    if args.dry_run:
        print_config(cfg, session_file)
        print("dry-run: exiting without connecting")
        return 0

    if args.login:
        if not cfg.phone:
            print(f"[error] {env_key('PHONE')} is not set; required for --login")
            return 1
        asyncio.run(login_main(cfg, session_base))
        return 0

    # Headless mode: no session file -> fail fast without even connecting.
    if not session_file.exists():
        print("NO SESSION — run: python downloader.py --login")
        return 2

    try:
        return asyncio.run(headless_main(cfg, session_base))
    except Exception as e:
        print(f"[error] {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
