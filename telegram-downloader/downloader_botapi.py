#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
from datetime import datetime, timedelta
import aiohttp

# ===============================================
# 1. CONFIGURATION (Using bot token)
# ===============================================

def get_config():
    """Load configuration from command-line arguments or environment variables."""
    config = {
        'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN'),
        'target_chat': os.environ.get('TELEGRAM_TARGET_CHAT', '39155241:c/2152949316'),
        'download_dir': os.environ.get('TELEGRAM_DOWNLOAD_DIR', '/Users/imma/Downloads/ebook-library/PT'),
        'allowed_extensions': os.environ.get('TELEGRAM_ALLOWED_EXTENSIONS', '.pdf,.epub').split(','),
        'limit': int(os.environ.get('TELEGRAM_MESSAGE_LIMIT', 100)),  # Messages per request
    }
    
    return config

config = get_config()
BOT_TOKEN = config['bot_token']
DOWNLOAD_DIR = config['download_dir']
ALLOWED_EXTENSIONS = [ext.strip() for ext in config['allowed_extensions']]

# Parse target chat ID (format: "X@c/Y" or just number)
target_chat_str = config['target_chat']
if '@' in target_chat_str:
    TARGET_CHAT_ID = int(target_chat_str.split('@')[1])
    TARGET_CHAT_TYPE = 'channel'  # c/ means channel
elif '/' in target_chat_str:
    TARGET_CHAT_ID = int(target_chat_str.split('/')[-1])
    TARGET_CHAT_TYPE = 'channel'  # c/ means channel
else:
    TARGET_CHAT_ID = int(target_chat_str)
    TARGET_CHAT_TYPE = 'chat'

print(f"[*] Bot Token loaded: {BOT_TOKEN}")
print(f"[*] Target Chat ID: {TARGET_CHAT_ID} ({TARGET_CHAT_TYPE})")
print(f"[*] Download Dir: {DOWNLOAD_DIR}")

# ===============================================
# 2. TELEGRAM BOT API CLIENT
# ===============================================

class TelegramBotAPI:
    """Wrapper for Telegram Bot API using aiohttp."""
    
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.telegram.org/bot" + token
        
    async def request(self, method, params=None):
        """Make a request to the Telegram Bot API."""
        url = f"{self.base_url}/{method}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=params) as response:
                return await response.json()
    
    async def get_updates(self, offset=None, limit=100):
        """Get updates from the bot."""
        params = {'offset': offset, 'limit': limit}
        return await self.request('getUpdates', params)
    
    async def get_message(self, chat_id, message_id):
        """Get a specific message."""
        params = {'chat_id': chat_id, 'message_id': message_id}
        return await self.request('getMessage', params)
    
    async def get_file(self, file_id):
        """Get file information."""
        params = {'file_id': file_id}
        return await self.request('getFile', params)
    
    async def download_file(self, file_path):
        """Download a file from the server."""
        async with aiohttp.ClientSession() as session:
            async with session.get(file_path) as response:
                if response.status == 200:
                    data = await response.read()
                    with open(file_path, 'wb') as f:
                        f.write(data)
                    return True
                return False
    
    async def get_chat_history(self, chat_id, limit=100):
        """Get chat history (messages)."""
        # Note: This method might not be available for all chat types
        params = {'chat_id': chat_id, 'limit': limit}
        return await self.request('getChat', params)

# ===============================================
# 3. DOWNLOAD FUNCTIONALITY
# ===============================================

async def download_file_from_message(bot_api, message):
    """Download file from a Telegram message using Bot API."""
    
    if not message.get('has_media'):
        return None
    
    media_type = message.get('media')
    
    if not media_type:
        return None
    
    # Handle different media types
    if media_type == 'photo':
        file_id = message.get('media', {}).get('file_id')
    elif media_type == 'video':
        file_id = message.get('media', {}).get('file_id')
    elif media_type == 'document':
        file_id = message.get('media', {}).get('file_id')
    else:
        return None
    
    if not file_id:
        return None
    
    # Get file info
    try:
        file_info = await bot_api.get_file(file_id)
        
        if not file_info.get('file_path'):
            return None
        
        # Download the file
        download_url = f"https://api.telegram.org/file{file_info['file_path']}"
        
        filename = message.get('media', {}).get('file_name', f'file_{message["id"]}.{ALLOWED_EXTENSIONS[0]}')
        
        # Check file extension
        ext = os.path.splitext(filename)[1].lower()
        
        if ext not in ALLOWED_EXTENSIONS:
            return None
        
        # Download and save the file
        download_path = os.path.join(DOWNLOAD_DIR, filename)
        
        success = await bot_api.download_file(download_url)
        
        if success:
            return filename
        
    except Exception as e:
        print(f"  [Error] Failed to download file {file_id}: {e}")
    
    return None

async def run_downloader(bot_api, chat_id, download_dir, allowed_extensions):
    """Download messages from a chat using Bot API."""
    
    downloaded_count = 0
    
    print(f"\n[*] Starting download from chat ID: {chat_id}")
    
    offset = 0
    
    while True:
        # Get updates (messages)
        try:
            updates = await bot_api.get_updates(offset=offset, limit=100)
        except Exception as e:
            print(f"  [Error] Failed to get updates: {e}")
            break
        
        if not updates.get('result'):
            break
        
        messages = updates['result']
        
        for message in messages:
            # Check if this is from our target chat
            if message.get('chat', {}).get('id') != chat_id:
                continue
            
            # Check message date (only download recent messages)
            try:
                msg_date = datetime.fromtimestamp(message['date'])
                # Only download messages from the last 24 hours
                if datetime.now() - msg_date > timedelta(hours=24):
                    continue
            except:
                pass
            
            # Download file from message
            filename = await download_file_from_message(bot_api, message)
            
            if filename:
                print(f"  [Downloaded] {filename}")
                downloaded_count += 1
        
        if not messages:
            break
        
        offset = updates.get('next_offset')
        
        # Safety check to prevent infinite loop
        if downloaded_count > 1000:
            print(f"[*] Safety limit reached. Downloading {downloaded_count} files.")
            break
    
    return downloaded_count

# ===============================================
# 4. MAIN FUNCTION
# ===============================================

async def main():
    """Main function to start the download process."""
    
    print(f"\n========================================")
    print("Telegram Bot Downloader")
    print("========================================\n")
    
    # Initialize bot API
    bot_api = TelegramBotAPI(BOT_TOKEN)
    
    try:
        # Download files from target chat
        downloaded_count = await run_downloader(bot_api, TARGET_CHAT_ID, DOWNLOAD_DIR, ALLOWED_EXTENSIONS)
        
        # Final report
        print("\n================================================")
        print("[SUCCESS] Download completed!")
        print(f"Total files downloaded: {downloaded_count}")
        print(f"All files saved to: {DOWNLOAD_DIR}")
        print("================================================\n")
        
    except Exception as e:
        print(f"\n[FATAL ERROR] Download failed!")
        print(f"Error details: {e}")
    
    finally:
        await bot_api.request('getMe')  # Clean up

if __name__ == "__main__":
    asyncio.run(main())
