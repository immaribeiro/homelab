---
created: 2026-08-16
updated: 2026-08-16
---

# 🔗 Connecting to the Obsidian Vault from Other Machines

## Architecture

```
Mac Mini (imma-mini)                    MacBook Air (macbook-air)
  ~/GitHub/homelab/hermes/vault/   ←SMB over Tailscale→  /Volumes/Hermes Vault/
  (single source of truth)                                    (mounted, read/write)
         │
         └→ Opened in Obsidian on both machines
```

The vault lives **only on the Mac Mini**. Other machines mount it as a network drive over Tailscale. No sync, no conflicts, one source of truth.

## Setup: Mac Mini (Already Done ✅)

- SMB share "Hermes Vault" created at `/Users/imma/GitHub/homelab/hermes/vault`
- SMB service listening on port 445
- Tailscale IP: `100.101.63.91`
- Firewall: disabled
- Share is read-write for user `imma`

## Setup: MacBook Air (Do This)

### Step 1: Install Obsidian

```bash
brew install --cask obsidian
```

### Step 2: Mount the Vault Share

1. Open **Finder**
2. Menu bar → **Go** → **Connect to Server…** (or `⌘K`)
3. Enter this address:
   ```
   smb://100.101.63.91/Hermes Vault
   ```
   (spaces in "Hermes Vault" are fine — Finder handles them)
4. Click **Connect**
5. When prompted, enter:
   - **Name**: `imma` (your Mac Mini username)
   - **Password**: your Mac Mini login password
6. Check **"Remember this password in my keychain"** so you don't have to re-enter it
7. The share mounts at `/Volumes/Hermes Vault/`

### Step 3: Open the Vault in Obsidian

1. Open **Obsidian**
2. Click **Open folder as vault**
3. Navigate to **Hermes Vault** (under "Shared" or "Network" in Finder sidebar)
4. Select the folder and click **Open**

You should now see all the vault notes: README, agents/, notes/, etc.

### Step 4: Create an Automount (Optional but Recommended)

So the share reconnects automatically on reboot:

1. Open **System Settings** → **General** → **Login Items**
2. Add a new login item: navigate to `/Volumes/Hermes Vault`
3. Or add to **System Settings** → **Sharing** → nothing needed on Air side

Alternatively, add this to a login script:
```bash
# Save as ~/Library/LaunchAgents/com.user.mount-hermes-vault.plist
# Or just add to shell profile:
mount_smbfs //imma@100.101.63.91/Hermes\ Vault /Volumes/Hermes\ Vault
```

## Using the Vault from Both Machines

### Real-time Editing
Both machines see the same files. If you edit a note on the MacBook Air, it's instantly changed on the Mac Mini. No sync needed.

### Hermes Integration
On the Mac Mini, Hermes can read/write the vault via the `obsidian` skill (OBSIDIAN_VAULT_PATH is set). On the MacBook Air, you just use the Obsidian UI.

### Git (Bonus)
The vault is also in git. If you want to make changes locally on the MacBook Air without the network mount, you can clone the repo:
```bash
git clone https://github.com/immaribeiro/homelab.git ~/GitHub/homelab
```
Then open `~/GitHub/homelab/hermes/vault/` in Obsidian locally.

## Troubleshooting

### Can't connect to SMB share
- Verify Tailscale is running on both machines: `tailscale status`
- Verify port 445 is reachable: `nc -z 100.101.63.91 445`
- Try connecting by hostname: `smb://imma-mini/Hermes Vault`

### Share disconnects after sleep
- macOS may drop SMB connections after sleep. Reconnect via Finder → Go → Recent Servers
- Or use an automount script (see Step 4 above)

### Obsidian can't see .obsidian folder
- The `.obsidian/` folder is hidden in Finder. In Obsidian, use "Open folder as vault" and navigate to the mounted share directly.
- If Obsidian doesn't see it, create a symlink: `ln -s /Volumes/Hermes\ Vault ~/HermesVault` and open the symlink.

### Performance
- Over Tailscale (WireGuard), SMB is fast enough for Obsidian's text files.
- For large binary assets, it may be slower than local. Keep images small.

## Adding More Machines

Any machine on the Tailnet can mount the share:
```bash
# Linux
mount -t cifs //100.101.63.91/Hermes\ Vault /mnt/hermes-vault -o username=imma

# macOS
smb://100.101.63.91/Hermes Vault
```
