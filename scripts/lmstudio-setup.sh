#!/bin/bash
# LM Studio Setup Script for Homelab
# Installs LM Studio and configures it for homelab use

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOMELAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🚀 LM Studio Homelab Setup"
echo "=========================="
echo ""

# Load .env if exists
if [ -f "$HOMELAB_ROOT/.env" ]; then
    source "$HOMELAB_ROOT/.env"
fi

# Step 1: Install LM Studio
echo "📦 Step 1: Installing LM Studio..."
if [ -d "/Applications/LM Studio.app" ]; then
    echo "   ✓ LM Studio already installed"
else
    echo "   Installing via Homebrew..."
    brew install --cask lm-studio || {
        echo "   ⚠ Homebrew install failed. Download manually from https://lmstudio.ai"
        open "https://lmstudio.ai"
        echo "   Press Enter after installing LM Studio..."
        read
    }
fi

# Step 2: Get Mac IP
echo ""
echo "🌐 Step 2: Detecting Mac IP address..."
MAC_IP=$(ifconfig | grep "inet " | grep -v "127.0.0.1" | head -1 | awk '{print $2}')
echo "   Detected IP: $MAC_IP"
echo ""

# Step 3: Update .env
echo "💾 Step 3: Updating .env configuration..."
if ! grep -q "MAC_IP=" "$HOMELAB_ROOT/.env" 2>/dev/null; then
    echo "MAC_IP=$MAC_IP" >> "$HOMELAB_ROOT/.env"
    echo "   ✓ Added MAC_IP=$MAC_IP to .env"
else
    echo "   ℹ MAC_IP already set in .env"
fi

# Step 4: Launch LM Studio
echo ""
echo "🖥️  Step 4: Launching LM Studio..."
open -a "LM Studio"
echo "   ✓ LM Studio opened"
echo ""

# Instructions
echo "📋 Next Steps:"
echo "=============="
echo ""
echo "1. In LM Studio, go to 'Search' tab and download a model:"
echo "   Recommended: Llama 3.2 3B (search 'llama-3.2-3b-instruct')"
echo "   - Look for GGUF format"
echo "   - Choose Q4_K_M quantization for balance"
echo ""
echo "2. Go to 'Local Server' tab:"
echo "   - Select your downloaded model"
echo "   - Enable 'Allow remote connections'"
echo "   - Click 'Start Server'"
echo "   - Verify it shows: Running on http://0.0.0.0:1234"
echo ""
echo "3. Test the API from your Mac:"
echo "   make lm-test"
echo ""
echo "4. Deploy to cluster (makes LM Studio accessible from K8s):"
echo "   make lm-deploy"
echo ""
echo "5. 🌟 Deploy Web Chat UI (ChatGPT-style interface):"
echo "   make deploy-chat"
echo "   make tunnel-route HOST=llm.immas.org"
echo "   # Then access at: https://llm.immas.org"
echo ""
echo "6. (Alternative) Expose API externally via Cloudflare Tunnel:"
echo "   - Uncomment Ingress in k8s/manifests/lmstudio-external.yml"
echo "   - Add to k8s/cloudflared/tunnel.yaml ingress section:"
echo "     - hostname: llm.immas.org"
echo "       service: http://lmstudio.ai.svc.cluster.local:1234"
echo "   - Run: make tunnel-route HOST=llm.immas.org"
echo ""
echo "📖 Documentation:"
echo "   - LM Studio setup: $HOMELAB_ROOT/LMSTUDIO.md"
echo "   - Web Chat UI: $HOMELAB_ROOT/CHAT_UI.md"
echo "   - Quick reference: $HOMELAB_ROOT/LMSTUDIO_QUICKREF.md"
echo ""
