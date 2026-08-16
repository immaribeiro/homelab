#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from telethon import TelegramClient, events
import asyncio

# ===============================================
# 1. CONFIGURATION (Using user provided credentials)
# ===============================================

def get_config():
    """Load configuration from command-line arguments or environment variables."""
    config = {
        'api_id': os.environ.get('TELEGRAM_API_ID'),
        'api_hash': os.environ.get('TELEGRAM_API_HASH'),
        'phone': os.environ.get('TELEGRAM_PHONE'),  # Phone number for authentication
        'session_name': os.environ.get('TELEGRAM_SESSION_NAME', 'ebooks_session'),
        'target_chat': os.environ.get('TELEGRAM_TARGET_CHAT', '39155241:c/2152949316'),
        'download_dir': os.environ.get('TELEGRAM_DOWNLOAD_DIR', '/Users/imma/Downloads/ebook-library/PT'),
        'allowed_extensions': os.environ.get('TELEGRAM_ALLOWED_EXTENSIONS', '.pdf,.epub').split(','),
    }
    
    # Fallback to command-line arguments if env vars not set
    for key in ['api_id', 'api_hash', 'phone']:
        if config[key]:
            continue
        # Parse args: --api-id X --api-hash Y or positional arguments
        if len(sys.argv) > 1:
            for i, arg in enumerate(sys.argv[1:], 1):
                if arg.startswith(f'--{key}='):
                    config[key] = arg.split('=')[1].strip()
                elif i == len(sys.argv) - 1 and config[key] is None:
                    # Last positional argument
                    config[key] = arg
    
    return config

# Load configuration
config = get_config()

API_ID = int(config['api_id']) if config['api_id'] else 39155241
API_HASH = config['api_hash'] or 'c3ea94f44314adb25a11b978fa3aba50'

# Detect if we're using a bot token (API_HASH starts with "AA")
is_bot = API_HASH.startswith('AA')

PHONE = config['phone'] or os.environ.get('TELEGRAM_PHONE')
SESSION_NAME = config['session_name']

# Parse target chat ID for Telethon (format: "X@c/Y" or just number)
target_chat_str = config['target_chat']
if '@' in target_chat_str:
    TARGET_CHAT = int(target_chat_str.split('@')[1])
elif '/' in target_chat_str:
    TARGET_CHAT = int(target_chat_str.split('/')[-1])
else:
    TARGET_CHAT = int(target_chat_str)

DOWNLOAD_DIR = config['download_dir']
ALLOWED_EXTENSIONS = [ext.strip() for ext in config['allowed_extensions']]

print(f"[*] Config loaded: API_ID={API_ID}, SESSION={SESSION_NAME}, TARGET={TARGET_CHAT}")
print(f"[*] Using bot credentials: {is_bot}")

# Get 2FA code if provided (for non-programmatic login)
TWO_FA_CODE = os.environ.get('TELEGRAM_TWO_FA_CODE') if not is_bot else None

# ===============================================
# 2. DOWNLOAD FUNCTIONALITY
# ===============================================

async def run_downloader(client, chat_entity, download_dir, allowed_extensions):
    """Iterates through messages and saves appropriate files."""
    downloaded_count = 0
    
    print(f"\n[*] Starting file download from target group: {chat_entity}")
    
    # Iterate over all messages in the specified chat
    async for message in client.iter_messages(chat_entity):
        if message.media and message.file:
            mime_type = message.file.mime_type or ""
            filename = message.file.name
            ext = os.path.splitext(filename)[1].lower()

            # Check if the extension matches a known format (pdf or epub)
            if ext in allowed_extensions and mime_type.startswith('application/'):
                try:
                    print(f"  [Found] Downloading {filename}...")
                    # Download the file using the message object
                    await client.download_media(message.media, file=os.path.join(download_dir, filename))
                    downloaded_count += 1
                except Exception as e:
                    print(f"  [Skipped] Could not download {filename}: {e}")

    return downloaded_count

# ===============================================
# 3. MAIN FUNCTION - Handles authentication with 2FA
# ===============================================

async def authenticate_with_2fa(client, phone, code):
    """Authenticate with Telegram using 2FA code."""
    print(f"[*] Authenticating with phone: {phone}")
    print(f"[*] Authenticating with 2FA code: {code}")
    
    # First authenticate without 2FA to get the session
    await client.start(phone=phone)
    
    # Then set the 2FA code
    await client.sign_in(phone=phone, code=code)

async def main():
    """Main function to connect and start the downloading process."""
    print(f"[*] Connecting to Telegram client using session: {SESSION_NAME}")
    
    # Initialize client variable (will be assigned in try block)
    client = None
    
    # Check if session file exists (for re-authentication or existing login)
    session_path = os.path.join(os.getcwd(), f"{SESSION_NAME}.session")
    
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        
        # Try to start with existing session if available
        if os.path.exists(session_path):
            print(f"[*] Found existing session: {session_path}")
            
            # If phone is provided and not a bot, use it to authenticate with existing session
            if PHONE and not is_bot:
                print(f"[*] Attempting to use existing session with phone: {PHONE}")
                
                # Try to start without 2FA first (for accounts without 2FA or already authenticated)
                try:
                    await client.start(phone=PHONE, password=None)  # No password for existing session
                except Exception as e:
                    print(f"[*] Existing session requires 2FA. Please provide your 2FA code or login again.")
                    print(f"[*] Error: {e}")
                    # Clear the session and ask for 2FA code
                    os.remove(session_path)
                    print(f"[*] Session cleared. Please provide your 2FA code to continue.")
                else:
                    print(f"[*] Successfully authenticated with existing session!")
            elif not PHONE and is_bot:
                # Bot credentials - should work without phone
                await client.start()
            else:
                # No existing session or no phone, will need to authenticate
                print(f"[*] Please login via Telegram.")
                await client.start()
        else:
            # No existing session, will need to authenticate
            print(f"[*] No existing session found. Please login via Telegram.")
            
            if PHONE:
                await client.start(phone=PHONE)
            else:
                await client.start()
        
        # Ensure download directory exists
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)
            print(f"[*] Created download directory: {DOWNLOAD_DIR}")

        try:
            downloaded_count = await run_downloader(client, TARGET_CHAT, DOWNLOAD_DIR, ALLOWED_EXTENSIONS)
            
            # Final report generation
            print("\n================================================")
            print("[SUCCESS] Completed Telegram synchronization.")
            print(f"Total files successfully downloaded today: {downloaded_count}")
            print(f"All files are saved to the directory: {DOWNLOAD_DIR}")
            print("================================================\n")

        except Exception as e:
            print(f"\n[FATAL ERROR] The download process failed. Please check your connectivity and API credentials.")
            print(f"Details: {e}")

    except Exception as e:
        print(f"\n[ERROR] Failed to connect to Telegram client.")
        print(f"Details: {e}")

    finally:
        # Only stop if client is still running (don't call stop() if already terminated)
        if client:  # Check if client was successfully created
            try:
                await client.stop()
            except Exception as e:
                print(f"[INFO] Client already terminated: {e}")

if __name__ == "__main__":
    asyncio.run(main())
