# Open WebUI Chat Interface for LM Studio

Web-based ChatGPT-like interface for your homelab's LM Studio instance running on Mac bare metal.

**Access:** https://llm.immas.org

## Overview

This is your homelab's **only LLM chat interface**, connecting to LM Studio running on your Mac (192.168.1.231). The web UI runs in Kubernetes while LM Studio runs natively on macOS for optimal performance.

## Features

- 🎨 **Modern UI**: Beautiful, responsive ChatGPT-style interface
- 💬 **Full Chat**: Multi-turn conversations with context
- 📝 **Markdown Support**: Code blocks, tables, formatting
- 📚 **Chat History**: Save and resume conversations
- 👥 **Multi-User**: User accounts with auth
- 🔄 **Model Switching**: Switch between LM Studio models
- 📤 **Export**: Download chat history as JSON/Markdown
- 🌙 **Dark Mode**: Eye-friendly interface

## Quick Deploy

```bash
# 1. Ensure LM Studio is running
make lm-status

# 2. Deploy LM Studio service to cluster (if not done)
make lm-deploy

# 3. Deploy Open WebUI
make deploy-chat

# 4. Route DNS via Cloudflare Tunnel
make tunnel-route HOST=llm.immas.org

# 5. Access at https://llm.immas.org
```

## First-Time Setup

### 1. Create Admin Account

When you first visit https://llm.immas.org:

1. Click **Sign Up**
2. Enter email and password
3. **First user becomes admin automatically**
4. You'll be logged in immediately

### 2. Configure Models

Open WebUI auto-discovers models from LM Studio:

1. Click the model dropdown (top of chat)
2. Select your loaded LM Studio model
3. Start chatting!

**Note:** If no models appear, ensure LM Studio server is running and loaded.

### 3. Optional: Disable Signups

After creating your admin account, disable public signups:

```bash
kubectl -n chat set env deploy/open-webui ENABLE_SIGNUP=false
```

## Usage

### Basic Chat

1. Visit https://llm.immas.org
2. Log in with your account
3. Select a model from dropdown
4. Type your message and press Enter
5. View AI response in real-time

### Multi-Turn Conversations

Open WebUI maintains conversation context:

```
You: What is Kubernetes?
AI: Kubernetes is a container orchestration platform...

You: How do I deploy a pod?
AI: [AI remembers we're talking about Kubernetes]
```

### Chat History

- **Save**: Chats auto-save as you type
- **Resume**: Click on previous chats in sidebar
- **Search**: Find old conversations
- **Export**: Download as Markdown or JSON
- **Delete**: Remove unwanted chats

### Model Settings

Click **⚙️ Settings** → **Models**:

- **Temperature**: 0.0-2.0 (creativity)
- **Top P**: Nucleus sampling
- **Max Tokens**: Response length limit
- **System Prompt**: Override default behavior

### System Prompts

Customize AI behavior per chat:

```
You are a Kubernetes expert. Provide kubectl commands when relevant.
```

```
You are a Python tutor. Explain concepts with code examples.
```

```
You are a DevOps assistant for my homelab. Be concise.
```

## Administration

### Admin Panel

As admin user, access **⚙️ Admin Panel**:

- **Users**: Manage accounts, roles
- **Settings**: Global configuration
- **Models**: Configure model defaults
- **Connections**: Monitor active sessions

### User Management

```bash
# View users (via logs)
make chat-logs | grep "User created"

# Reset admin password (requires database access)
kubectl -n chat exec -it deploy/open-webui -- /bin/bash
# Inside container:
# sqlite3 /app/backend/data/webui.db
# UPDATE user SET password='...' WHERE email='admin@example.com';
```

### Backup Chat Data

```bash
# Backup persistent volume
kubectl -n chat exec deploy/open-webui -- tar czf - /app/backend/data > chat-backup-$(date +%Y%m%d).tar.gz

# Restore
kubectl -n chat exec -i deploy/open-webui -- tar xzf - -C / < chat-backup-20240101.tar.gz
```

## Configuration

### Environment Variables

Edit `k8s/manifests/open-webui.yml`:

```yaml
env:
- name: OPENAI_API_BASE_URLS
  value: "http://lmstudio.ai.svc.cluster.local:1234/v1"
  
- name: WEBUI_NAME
  value: "My Custom Name"
  
- name: ENABLE_SIGNUP
  value: "false"  # Disable after first user
  
- name: DEFAULT_MODELS
  value: "local-model"
  
- name: ENABLE_COMMUNITY_SHARING
  value: "false"
```

Apply changes:
```bash
kubectl apply -f k8s/manifests/open-webui.yml
kubectl -n chat rollout restart deploy/open-webui
```

### Connect to Multiple LLM Backends

Open WebUI supports multiple API endpoints (optional):

```yaml
- name: OPENAI_API_BASE_URLS
  value: "http://lmstudio.ai.svc.cluster.local:1234/v1"
```

You can add additional endpoints separated by semicolons if needed.

### Custom Branding

```yaml
- name: WEBUI_NAME
  value: "Homelab AI"
- name: WEBUI_URL
  value: "https://llm.immas.org"
- name: DEFAULT_LOCALE
  value: "en-US"
```

## Troubleshooting

### "No models found"

**Cause:** LM Studio not running or not accessible

**Fix:**
```bash
# Check LM Studio
make lm-status

# Check cluster service
kubectl -n ai get svc lmstudio
kubectl -n ai get endpoints lmstudio

# Test from pod
kubectl run -it --rm curl --image=curlimages/curl --restart=Never -- \
  curl http://lmstudio.ai.svc.cluster.local:1234/v1/models
```

### Chat UI not loading

**Check deployment:**
```bash
make chat-status
make chat-logs
```

**Common issues:**
- Pod not ready: `kubectl -n chat describe pod -l app=open-webui`
- PVC not bound: `kubectl -n chat get pvc`
- Ingress misconfigured: `kubectl -n chat get ingress`

### Slow responses

**Causes:**
- LM Studio using large model
- Low Mac resources
- Network latency

**Fix:**
```bash
# Use smaller/faster model in LM Studio (3B instead of 7B)
# Or adjust timeout in ingress
kubectl -n chat patch ingress open-webui --type=json \
  -p='[{"op":"add","path":"/metadata/annotations/nginx.ingress.kubernetes.io~1proxy-read-timeout","value":"1200"}]'
```

### "Connection refused"

**Check MAC_IP in endpoints:**
```bash
kubectl -n ai get endpoints lmstudio -o yaml
# Should show your Mac's IP (e.g., 192.168.1.100)

# Update if needed
kubectl -n ai delete endpoints lmstudio
# Then edit k8s/manifests/lmstudio-external.yml with correct IP
make lm-deploy
```

### Can't sign up

**If ENABLE_SIGNUP=false:**
```bash
# Enable temporarily
kubectl -n chat set env deploy/open-webui ENABLE_SIGNUP=true

# After signup
kubectl -n chat set env deploy/open-webui ENABLE_SIGNUP=false
```

### DNS not resolving

```bash
# Route with Cloudflare Tunnel
make tunnel-route HOST=llm.immas.org

# Verify
make verify-host HOST=llm.immas.org

# Manual test
dig llm.immas.org
curl -I https://llm.immas.org
```

## Management Commands

```bash
# Deploy
make deploy-chat

# Check status
make chat-status

# View logs
make chat-logs

# Restart
make chat-restart

# Update image to latest
kubectl -n chat set image deploy/open-webui \
  open-webui=ghcr.io/open-webui/open-webui:main
kubectl -n chat rollout status deploy/open-webui
```

## Advanced Features

### RAG (Retrieval-Augmented Generation)

Open WebUI supports document upload:

1. Click **+** → **Upload Document**
2. Upload PDF, TXT, Markdown
3. AI can reference document content
4. Ask questions about uploaded files

### Custom Functions

Write Python functions that extend the UI:

1. Admin Panel → **Functions**
2. Create new function
3. Python code with special decorators
4. Use in chats with `#function-name`

### API Access

Open WebUI provides its own API:

```bash
# Get API key from Settings → Account → API Keys

# Test
curl https://llm.immas.org/api/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Webhooks

Trigger external actions from chat:

1. Admin Panel → **Settings** → **Webhooks**
2. Add webhook URL
3. Events: message sent, user created, etc.
4. Integrate with Home Assistant, Telegram, etc.

## Security

### Best Practices

1. **Disable signups** after creating accounts
2. **Strong passwords** for all users
3. **HTTPS only** (handled by ingress)
4. **Regular backups** of chat data
5. **Update regularly** to latest image

### Network Security

```yaml
# Restrict to internal network only (remove ingress)
# Access via kubectl port-forward

kubectl -n chat port-forward svc/open-webui 8080:8080
# Then: http://localhost:8080
```

### User Roles

- **Admin**: Full access, user management
- **User**: Chat access only
- **Pending**: Awaiting approval (if enabled)

## Integration Examples

### Home Assistant

Create a REST command:

```yaml
# configuration.yaml
rest_command:
  ask_ai:
    url: https://llm.immas.org/api/chat/completions
    method: POST
    headers:
      Authorization: "Bearer YOUR_API_KEY"
      Content-Type: "application/json"
    payload: >
      {
        "model": "local-model",
        "messages": [{"role": "user", "content": "{{ message }}"}]
      }
```

### Telegram Bot

Forward messages to Open WebUI API:

```python
import requests

def ask_webui(question):
    response = requests.post(
        "https://llm.immas.org/api/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "local-model",
            "messages": [{"role": "user", "content": question}]
        }
    )
    return response.json()["choices"][0]["message"]["content"]
```

### Homepage Dashboard

Add to `k8s/manifests/home.yml` services:

```yaml
- AI:
    - Chat Assistant:
        href: https://llm.immas.org
        icon: si-openai
        description: LM Studio Web UI
```

## Resources

- **Open WebUI Docs**: https://docs.openwebui.com
- **GitHub**: https://github.com/open-webui/open-webui
- **LM Studio**: https://lmstudio.ai
- **Homelab Guide**: See LMSTUDIO.md

## Comparison with Alternatives

| Feature | Open WebUI | LobeChat | ChatGPT-Next-Web |
|---------|------------|----------|------------------|
| UI Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| User Auth | ✅ Built-in | ❌ Basic | ❌ Basic |
| RAG Support | ✅ Yes | ✅ Yes | ❌ No |
| Multi-User | ✅ Yes | ⚠️ Limited | ❌ No |
| Admin Panel | ✅ Full | ❌ No | ❌ No |
| Mobile | ✅ PWA | ✅ PWA | ✅ PWA |
| Docker Image | 600MB | 400MB | 300MB |

**Recommendation:** Open WebUI for production homelab use.

## Next Steps

1. ✅ Deploy: `make deploy-chat`
2. ✅ Route DNS: `make tunnel-route HOST=llm.immas.org`
3. ✅ Create admin account
4. ✅ Disable signups
5. 🚀 Start chatting with your local LLM!
6. 🔗 Add to Homepage dashboard
7. 📱 Create PWA bookmark on mobile
8. 🤖 Integrate with other homelab services

Enjoy your self-hosted ChatGPT alternative! 🎉
