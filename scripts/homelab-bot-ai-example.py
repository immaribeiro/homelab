#!/usr/bin/env python3
"""
Example: Enhanced Homelab Telegram Bot with LM Studio Integration

This is an example showing how to add LLM capabilities to your homelab bot.
Based on the existing scripts/homelab-bot.py but with AI features.

DO NOT replace the existing bot - this is just for reference.
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("CHAT_ID", "0"))
LMSTUDIO_URL = os.getenv("LMSTUDIO_URL", "http://lmstudio.ai.svc.cluster.local:1234/v1")

# Configure LM Studio client (OpenAI-compatible)
openai.api_base = LMSTUDIO_URL
openai.api_key = "not-needed"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask the local LLM a question"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /ask <your question>")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text("🤔 Thinking...")
    
    try:
        response = openai.ChatCompletion.create(
            model="local-model",
            messages=[
                {"role": "system", "content": "You are a helpful homelab assistant. Be concise."},
                {"role": "user", "content": question}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content
        await update.message.reply_text(f"🤖 {answer}")
        
    except Exception as e:
        logger.error(f"LM Studio error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def analyze_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Use AI to analyze pod logs (example)"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    # In a real implementation, you'd fetch actual logs
    sample_logs = """
    2024-01-01 10:00:00 ERROR Failed to connect to database
    2024-01-01 10:00:05 INFO Retrying connection...
    2024-01-01 10:00:10 ERROR Connection timeout
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="local-model",
            messages=[
                {"role": "system", "content": "You are a DevOps expert. Analyze logs and suggest solutions."},
                {"role": "user", "content": f"Analyze these logs:\n\n{sample_logs}"}
            ],
            max_tokens=400
        )
        
        analysis = response.choices[0].message.content
        await update.message.reply_text(f"📊 Log Analysis:\n\n{analysis}")
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available AI commands"""
    if update.effective_chat.id != ALLOWED_CHAT_ID:
        return
    
    help_text = """
🤖 *AI Commands:*
/ask <question> - Ask the LLM anything
/analyze - Analyze recent pod logs (demo)
/summarize - Summarize cluster status

📦 *Regular Commands:*
/status - Check homelab status
/help - Show this message
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # AI command handlers
    app.add_handler(CommandHandler("ask", ask_ai))
    app.add_handler(CommandHandler("analyze", analyze_logs))
    app.add_handler(CommandHandler("help", help_command))
    
    logger.info("🚀 Homelab AI Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

"""
DEPLOYMENT EXAMPLE:
===================

1. Update k8s/manifests/homelab-bot.yml to include LMSTUDIO_URL:
   
   env:
   - name: LMSTUDIO_URL
     value: "http://lmstudio.ai.svc.cluster.local:1234/v1"

2. Ensure openai package is in requirements:
   pip install openai

3. Deploy:
   kubectl apply -f k8s/manifests/homelab-bot.yml

4. Test:
   Send to Telegram: /ask What is Kubernetes?

FEATURES YOU COULD ADD:
========================

- Cluster diagnostics: "Why is pod X crashing?"
- Natural language queries: "Show me high CPU pods"
- Log summarization: Analyze last 100 lines
- Alert triage: AI explains what the alert means
- Automated responses: AI suggests kubectl commands
- Home automation: "Turn off lights when nobody's home"
- Document Q&A: Ask questions about your homelab docs

SECURITY NOTES:
===============

- Always validate ALLOWED_CHAT_ID
- Don't expose sensitive data to LLM
- Rate limit AI requests (costs compute)
- Log all AI interactions for audit
- Consider adding content filtering
"""
