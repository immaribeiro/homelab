# LM Studio Quick Reference

## Web Chat UI (Recommended!)

```bash
# Deploy ChatGPT-style web interface
make deploy-chat
make tunnel-route HOST=chat.immas.org

# Access at: https://chat.immas.org
# First user becomes admin
```

See [CHAT_UI.md](./CHAT_UI.md) for full web interface documentation.

## Installation & Setup

```bash
# One-line setup
bash scripts/lmstudio-setup.sh

# Or step by step
brew install --cask lm-studio
open -a "LM Studio"
# Download model (Search → llama-3.2-3b)
# Start server (Local Server → Start)
```

## Make Targets

```bash
# LM Studio API
make lm-install    # Install LM Studio via Homebrew
make lm-status     # Check if server is running
make lm-test       # Test API with sample request
make lm-deploy     # Create K8s service (requires MAC_IP in .env)

# Web Chat UI
make deploy-chat   # Deploy Open WebUI (ChatGPT-style interface)
make chat-status   # Check chat UI status
make chat-logs     # View chat UI logs
make chat-restart  # Restart chat UI
```

## Quick Access

- **Chat UI**: https://chat.immas.org (web interface)
- **API (Local)**: http://localhost:1234/v1 (Mac)
- **API (Cluster)**: http://lmstudio.ai.svc.cluster.local:1234/v1 (K8s)

## API Endpoints

**Base URL (Local):** `http://localhost:1234/v1`  
**Base URL (Cluster):** `http://lmstudio.ai.svc.cluster.local:1234/v1`

```bash
# List models
curl http://localhost:1234/v1/models

# Chat completion
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Recommended Models

| Model | Size | Use Case | Speed |
|-------|------|----------|-------|
| Llama 3.2 3B | ~2GB | Fast chat, simple tasks | ⚡⚡⚡ |
| Phi-3 Mini | ~2GB | Efficient, good quality | ⚡⚡⚡ |
| Mistral 7B | ~4GB | Balanced quality/speed | ⚡⚡ |
| Llama 3.1 8B | ~5GB | High quality responses | ⚡ |

**Quantization:** Q4_K_M (recommended for balance)

## Configuration

### Allow Remote Access
1. LM Studio → Local Server
2. Enable "Allow remote connections"
3. Click "Start Server"
4. Verify: `Running on http://0.0.0.0:1234`

### Set MAC_IP in .env
```bash
# Get your Mac's IP
ifconfig | grep "inet " | grep -v 127.0.0.1

# Add to .env
echo "MAC_IP=192.168.1.100" >> .env
```

## Integration Examples

### Python
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="local-model",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### JavaScript
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

### Curl
```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [
      {"role": "system", "content": "You are helpful."},
      {"role": "user", "content": "Explain Docker"}
    ],
    "temperature": 0.7,
    "max_tokens": 200
  }'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server won't start | Check port 1234 not in use: `lsof -i :1234` |
| Cluster can't connect | Verify MAC_IP in .env, check firewall |
| Slow responses | Use smaller model (3B instead of 7B) |
| Out of memory | Reduce context length or use Q4 quantization |
| "Model not found" | Load model in UI first (Chat tab) |

## Expose Externally (Optional)

### Via Cloudflare Tunnel

1. Add to `k8s/cloudflared/tunnel.yaml`:
```yaml
ingress:
  - hostname: llm.immas.org
    service: http://lmstudio.ai.svc.cluster.local:1234
```

2. Route DNS:
```bash
make tunnel-route HOST=llm.immas.org
```

3. Test:
```bash
curl https://llm.immas.org/v1/models
```

## Performance Tips

**M4 Mac Mini Optimization:**
- Use Q4_K_M quantization
- GPU Layers: -1 (uses all available)
- Context: 4096 for chat, 8192 for documents
- Temperature: 0.7 (balanced creativity)

**Memory Usage:**
- 3B model: ~2-3GB RAM
- 7B model: ~4-6GB RAM
- 13B model: ~8-10GB RAM

## Files Created

```
homelab/
├── LMSTUDIO.md                           # Full documentation
├── scripts/lmstudio-setup.sh             # Setup script
├── scripts/homelab-bot-ai-example.py     # Integration example
├── k8s/manifests/lmstudio-external.yml   # K8s service
└── Makefile                              # Added lm-* targets
```

## Next Steps

1. ✅ Install: `bash scripts/lmstudio-setup.sh`
2. ✅ Download model (3B for speed, 7B for quality)
3. ✅ Start server
4. ✅ Test: `make lm-test`
5. ✅ Deploy to cluster: `make lm-deploy`
6. 🚀 Build integrations (Telegram bot, Home Assistant, etc.)

See **LMSTUDIO.md** for complete guide!
