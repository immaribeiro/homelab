# LM Studio Deployment Guide

Guide for deploying LM Studio on Mac (bare metal) for homelab LLM inference.

**Quick Start:** `bash scripts/lmstudio-setup.sh` then `make deploy-chat` for web UI.

## What is LM Studio?

LM Studio is a desktop application that allows you to:
- Download and run LLMs locally (Llama, Mistral, Phi, etc.)
- Run inference with OpenAI-compatible API
- Use a simple UI for model management
- No GPU required (optimized for Apple Silicon)

## Web Chat Interface

**For a ChatGPT-like web UI, see [CHAT_UI.md](./CHAT_UI.md)**

Quick deploy:
```bash
make deploy-chat              # Deploy Open WebUI
make tunnel-route HOST=chat.immas.org
# Access at: https://chat.immas.org
```

## Installation

### Option 1: Download from Website (Recommended)
```bash
# Visit https://lmstudio.ai and download for macOS
# Or use the direct download:
open "https://lmstudio.ai"
```

### Option 2: Using Homebrew Cask
```bash
brew install --cask lm-studio
```

## Initial Setup

1. **Launch LM Studio**
   ```bash
   open -a "LM Studio"
   ```

2. **Download a Model**
   - Click "Search" tab in LM Studio
   - Recommended models for M4 Mac Mini:
     - **Llama 3.2 3B** (fast, good for chat) - ~2GB
     - **Mistral 7B** (balanced quality/speed) - ~4GB
     - **Phi-3 Mini** (Microsoft, efficient) - ~2GB
     - **Llama 3.1 8B** (high quality) - ~5GB
   
   - Search for model name
   - Click download (GGUF format, Q4_K_M quantization recommended)

3. **Load a Model**
   - Go to "Chat" tab
   - Select model from dropdown
   - Click "Load Model"
   - Wait for loading (shows in bottom right)

## Running as API Server

LM Studio provides an OpenAI-compatible API server.

### Start Server via UI

1. Go to "Local Server" tab
2. Select your loaded model
3. Click "Start Server"
4. Default: `http://localhost:1234/v1`

### Start Server via CLI (Headless)

LM Studio can run headless for automation:

```bash
# Find the LM Studio CLI binary
export LMSTUDIO_CLI="/Applications/LM Studio.app/Contents/Resources/app.asar.unpacked/server/lms"

# Start server with specific model
$LMSTUDIO_CLI server start --model "path/to/model.gguf"

# Or let it auto-select the last used model
$LMSTUDIO_CLI server start
```

## Configuration

### Server Settings

In LM Studio → Local Server tab:
- **Port**: 1234 (default)
- **CORS**: Enable for web access
- **API Key**: Optional (can enable for security)

### Performance Tuning (M4 Mac Mini)

Recommended settings for different use cases:

**Fast Responses (Chat)**:
- Model: Llama 3.2 3B or Phi-3 Mini
- Context Length: 2048-4096
- GPU Layers: -1 (all layers on GPU/Neural Engine)

**High Quality (Long-form)**:
- Model: Llama 3.1 8B or Mistral 7B
- Context Length: 8192-16384
- GPU Layers: -1

**Memory Constrained**:
- Use Q4_K_M or Q5_K_M quantization
- Reduce context length to 2048
- GPU Layers: Auto

## Network Access from Cluster

To allow your K3s cluster to access the LM Studio API:

### Option 1: Direct Access via Mac IP

```bash
# Get your Mac's IP on the local network
ifconfig | grep "inet " | grep -v 127.0.0.1

# Example: 192.168.1.100
# Cluster can access: http://192.168.1.100:1234/v1
```

In LM Studio → Local Server:
- Enable "Allow remote connections"

### Option 2: Expose via Cloudflare Tunnel (Secure)

Create a tunnel from your cluster to your Mac:

```yaml
# Add to k8s/cloudflared/tunnel.yaml ingress section:
- hostname: llm.immas.org
  service: http://192.168.1.100:1234  # Your Mac IP
```

Then update DNS:
```bash
make tunnel-route HOST=llm.immas.org
```

### Option 3: Service in Kubernetes (Proxy)

Create a Kubernetes Service pointing to your Mac:

```yaml
# k8s/manifests/lmstudio-external.yml
apiVersion: v1
kind: Service
metadata:
  name: lmstudio
  namespace: ai
spec:
  type: ExternalName
  externalName: 192.168.1.100  # Your Mac IP
  ports:
  - port: 1234
    targetPort: 1234
    protocol: TCP
```

## Testing the API

### Basic Health Check

```bash
# From your Mac
curl http://localhost:1234/v1/models

# From cluster (using Mac IP)
kubectl run -it --rm curl --image=curlimages/curl --restart=Never -- \
  curl http://192.168.1.100:1234/v1/models
```

### Chat Completion Test

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is Kubernetes?"}
    ],
    "temperature": 0.7,
    "max_tokens": 200
  }'
```

### OpenAI-Compatible Libraries

Use standard OpenAI libraries by pointing to your LM Studio endpoint:

**Python**:
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed"  # LM Studio doesn't require API key by default
)

response = client.chat.completions.create(
    model="local-model",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)
print(response.choices[0].message.content)
```

**JavaScript/TypeScript**:
```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:1234/v1',
  apiKey: 'not-needed'
});

const response = await client.chat.completions.create({
  model: 'local-model',
  messages: [{ role: 'user', content: 'Hello!' }]
});
```

## Automation with Makefile

Add these targets to your homelab Makefile:

```bash
# Check if LM Studio server is running
make lm-status

# Test LM Studio API
make lm-test

# Deploy LM Studio external service to cluster
make lm-deploy
```

## Running on Boot (Optional)

To automatically start LM Studio server when your Mac boots:

### Option 1: LaunchAgent (Recommended)

Create `~/Library/LaunchAgents/ai.lmstudio.server.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.lmstudio.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/LM Studio.app/Contents/MacOS/LM Studio</string>
        <string>--server</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/lmstudio-server.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/lmstudio-server.error.log</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/ai.lmstudio.server.plist
```

### Option 2: Simple Startup Script

Create `~/scripts/start-lmstudio.sh`:
```bash
#!/bin/bash
open -a "LM Studio"
sleep 5
# If LM Studio supports CLI start, add that here
```

Add to System Preferences → Users & Groups → Login Items

## Use Cases in Your Homelab

### 1. Telegram Bot with LLM
Enhance your homelab bot with AI responses:

```python
# In scripts/homelab-bot.py
import openai

openai.api_base = "http://192.168.1.100:1234/v1"
openai.api_key = "not-needed"

def ask_llm(question):
    response = openai.ChatCompletion.create(
        model="local-model",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content
```

### 2. Home Assistant Integration
Create an automation that queries your local LLM:

```yaml
# Home Assistant automation example
automation:
  - alias: "Ask LLM about home status"
    trigger:
      platform: state
      entity_id: input_boolean.ask_status
    action:
      - service: rest_command.ask_lmstudio
        data:
          message: "Summarize home status"
```

### 3. Custom Dashboard Widget
Add LLM query widget to Homepage:

```yaml
# In Homepage widgets.yaml
- LLM Assistant:
    widget:
      type: custom
      url: http://192.168.1.100:1234/v1/models
      mappings:
        - field: data[0].id
          label: Current Model
```

## Model Recommendations by Use Case

**Quick Responses** (< 1s):
- Phi-3 Mini (3.8B) Q4_K_M
- Llama 3.2 3B Q4_K_M

**Balanced** (1-3s):
- Mistral 7B Q4_K_M
- Llama 3.1 8B Q4_K_M

**High Quality** (3-5s):
- Llama 3.1 8B Q5_K_M
- Mixtral 8x7B Q4_K_M (if you have 32GB+ RAM)

**Coding Tasks**:
- CodeLlama 7B/13B
- DeepSeek Coder 6.7B
- Qwen2.5-Coder 7B

## Monitoring & Logs

### Check LM Studio Status
```bash
# Check if server is running
curl -s http://localhost:1234/v1/models | jq .

# Monitor logs (if using LaunchAgent)
tail -f /tmp/lmstudio-server.log
```

### Performance Monitoring
```bash
# Watch CPU/Memory usage
top -pid $(pgrep "LM Studio")

# Or with Activity Monitor
open -a "Activity Monitor"
# Search for "LM Studio"
```

## Troubleshooting

### Server Won't Start
- Check port 1234 is not in use: `lsof -i :1234`
- Ensure model is loaded in UI first
- Check Console.app for crash logs

### Slow Responses
- Use smaller model or lower quantization
- Reduce context length
- Close other heavy apps
- Check Activity Monitor for memory pressure

### Cluster Can't Access
- Verify Mac IP: `ifconfig | grep "inet "`
- Check firewall: System Preferences → Security & Privacy → Firewall
- Ensure "Allow remote connections" is enabled in LM Studio
- Test from cluster: `kubectl run -it --rm curl --image=curlimages/curl --restart=Never -- curl http://MAC_IP:1234/v1/models`

### Model Download Issues
- Check disk space: `df -h ~`
- Models stored in: `~/.cache/lm-studio/` or `~/LM Studio/models/`
- Try different model source (HuggingFace mirror)

## Resources

- **LM Studio Docs**: https://lmstudio.ai/docs
- **Model Search**: https://huggingface.co/models?library=gguf
- **GGUF Format**: https://github.com/ggerganov/llama.cpp
- **OpenAI API Spec**: https://platform.openai.com/docs/api-reference

## Security Considerations

1. **API Key**: Enable API key in LM Studio for production
2. **Network**: Don't expose to public internet without authentication
3. **Cloudflare Tunnel**: Use for external access (includes DDoS protection)
4. **Rate Limiting**: Implement in your app layer if needed
5. **Content Filtering**: Add guardrails for production chatbots

## Next Steps

1. Install LM Studio: `brew install --cask lm-studio`
2. Download a model (recommended: Llama 3.2 3B)
3. Start local server
4. Test API: `make lm-test`
5. Integrate with homelab services
6. Optionally expose via Cloudflare Tunnel
