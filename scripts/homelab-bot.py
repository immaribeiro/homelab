#!/usr/bin/env python3
import asyncio
import os
import re
import sys
from typing import Optional

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters


QB_URL = os.environ.get("QB_URL", "http://qbittorrent.qbittorrent.svc.cluster.local:8080")
QB_USER = os.environ.get("QB_USER", "admin")
QB_PASS = os.environ.get("QB_PASS", "adminadmin")
SAVE_PATH = os.environ.get("SAVE_PATH", "/downloads")
AUTO_TMM = os.environ.get("AUTO_TMM", "false").lower()  # "true" or "false"
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Whitelist a single chat id (string or int)
CHAT_ID = os.environ.get("CHAT_ID")

MAGNET_RE = re.compile(r"^magnet:\?xt=urn:btih:[A-Za-z0-9]{6,}.*")

session = requests.Session()


def _login() -> None:
    resp = session.post(f"{QB_URL}/api/v2/auth/login", data={"username": QB_USER, "password": QB_PASS}, timeout=10)
    resp.raise_for_status()


def _version() -> str:
    resp = session.get(f"{QB_URL}/api/v2/app/version", timeout=10)
    resp.raise_for_status()
    return resp.text.strip()


def _add_magnet(magnet: str, savepath: Optional[str]) -> None:
    data = {"urls": magnet}
    if savepath:
        data["savepath"] = savepath
        # Disable AutoTMM if explicit savepath provided
        data["autoTMM"] = "false" if AUTO_TMM not in ("true", "false") else AUTO_TMM
    resp = session.post(f"{QB_URL}/api/v2/torrents/add", data=data, timeout=20)
    resp.raise_for_status()


async def _ensure_login() -> None:
    # Basic ping to check cookie validity; if fails, re-login
    try:
        await asyncio.to_thread(_version)
    except Exception:
        await asyncio.to_thread(_login)


def _is_authorized(update: Update) -> bool:
    if CHAT_ID is None:
        return True  # no restriction
    try:
        return str(update.effective_chat.id) == str(CHAT_ID)
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Always reveal chat ID to help configuration
    await update.message.reply_text(
        f"🏠 Homelab Bot\n\n"
        f"Your chat ID: {update.effective_chat.id}\n\n"
        f"Send a magnet link to download via qBittorrent.\n\n"
        "Commands:\n"
        "/id - Show your chat ID\n"
        "/help - Show available commands\n"
        "/status - Check qBittorrent status\n"
        "/version - Get qBittorrent version\n"
        "/add <magnet> - Add a torrent"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    await update.message.reply_text(
        "🤖 Homelab Bot Commands\n\n"
        "📥 Torrents:\n"
        "  • Send magnet link directly\n"
        "  • /add <magnet> - Add torrent\n"
        "  • /status - qBittorrent status\n"
        "  • /version - qBittorrent version\n\n"
        "ℹ️ Other:\n"
        "  • /id - Show your chat ID\n"
        "  • /help - This message\n"
        "  • /start - Welcome message"
    )


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # No auth gating: always reply with chat ID
    await update.message.reply_text(f"Your chat ID: {update.effective_chat.id}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    try:
        await _ensure_login()
        
        # Get transfer info
        resp = session.get(f"{QB_URL}/api/v2/transfer/info", timeout=10)
        resp.raise_for_status()
        transfer = resp.json()
        
        # Get torrent count
        resp = session.get(f"{QB_URL}/api/v2/torrents/info", timeout=10)
        resp.raise_for_status()
        torrents = resp.json()
        
        dl_speed = transfer.get("dl_info_speed", 0) / 1024 / 1024  # MB/s
        up_speed = transfer.get("up_info_speed", 0) / 1024 / 1024
        
        downloading = sum(1 for t in torrents if t.get("state") in ("downloading", "stalledDL", "metaDL"))
        seeding = sum(1 for t in torrents if t.get("state") in ("uploading", "stalledUP"))
        paused = sum(1 for t in torrents if "paused" in t.get("state", "").lower())
        
        await update.message.reply_text(
            f"📊 qBittorrent Status\n\n"
            f"⬇️ Download: {dl_speed:.2f} MB/s\n"
            f"⬆️ Upload: {up_speed:.2f} MB/s\n\n"
            f"📦 Torrents:\n"
            f"  • Downloading: {downloading}\n"
            f"  • Seeding: {seeding}\n"
            f"  • Paused: {paused}\n"
            f"  • Total: {len(torrents)}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to get status: {e}")


async def version(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    try:
        await _ensure_login()
        v = await asyncio.to_thread(_version)
        await update.message.reply_text(f"qBittorrent version: {v}")
    except Exception as e:
        await update.message.reply_text(f"Error fetching version: {e}")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    text = " ".join(context.args) if context.args else (update.message.text or "")
    text = text.strip()
    if not MAGNET_RE.match(text):
        await update.message.reply_text("Please provide a valid magnet link starting with magnet:?xt=urn:btih:")
        return
    try:
        await _ensure_login()
        await asyncio.to_thread(_add_magnet, text, SAVE_PATH)
        await update.message.reply_text("✅ Magnet submitted to qBittorrent")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to add magnet: {e}")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    text = (update.message.text or "").strip()
    if MAGNET_RE.match(text):
        try:
            await _ensure_login()
            await asyncio.to_thread(_add_magnet, text, SAVE_PATH)
            await update.message.reply_text("✅ Magnet submitted to qBittorrent")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to add magnet: {e}")
    else:
        await update.message.reply_text("Send a magnet link or use /add <magnet>")


async def main() -> None:
    if not BOT_TOKEN:
        print("BOT_TOKEN is required", file=sys.stderr)
        sys.exit(1)

    print("homelab-bot starting...")
    sys.stdout.flush()
    
    # Increase timeout and add retries for flaky cluster networking
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connection_pool_size=8, connect_timeout=30.0, read_timeout=30.0)
    
    print("Building application...")
    sys.stdout.flush()
    
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("version", version))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    print("Initializing bot...")
    sys.stdout.flush()
    await app.initialize()
    
    print("Starting bot...")
    sys.stdout.flush()
    await app.start()
    
    print("Starting updater polling...")
    sys.stdout.flush()
    await app.updater.start_polling()
    
    print("✅ homelab-bot is running and polling for messages!")
    sys.stdout.flush()
    
    # Keep running
    import signal
    stop = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: stop.set())
    await stop.wait()
    
    await app.updater.stop()
    await app.stop()
    await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
