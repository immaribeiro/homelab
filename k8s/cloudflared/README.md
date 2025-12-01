Cloudflare Tunnel (cloudflared)

Overview:
This setup establishes an outbound-only Cloudflare Tunnel so you can reach
`hello.immas.org` (and later other apps) without exposing inbound ports or
needing your mac to sit on the `lima0` network.

Prerequisites:
1. Install cloudflared locally (on your mac):
   brew install cloudflared
2. Authenticate:
   cloudflared tunnel login
3. Create a named tunnel (choose a name, e.g. homelab):
   cloudflared tunnel create homelab
   This outputs a UUID (TUNNEL_ID) and places credentials at:
   ~/.cloudflared/<TUNNEL_ID>.json
4. Create a public DNS CNAME route via Cloudflare (the ingress rules below will also work
   if you map at the Tunnel level):
   cloudflared tunnel route dns homelab hello.immas.org

Provide values as environment variables before running `make tunnel`:
 - TUNNEL_ID=<uuid from create>
 - TUNNEL_NAME=homelab (or your chosen name)
 - TUNNEL_CRED_FILE=~/.cloudflared/<TUNNEL_ID>.json

What happens:
- Secret `cloudflared-credentials` stores the credential JSON.
- ConfigMap `cloudflared-config` defines routing for hello.immas.org to the
  in-cluster ingress-nginx controller service via http://ingress-nginx-controller.ingress-nginx.svc.cluster.local:80
- Deployment runs cloudflared which establishes the tunnel.

Extend routes:
Edit the configmap and add lines under ingress: `- hostname: ha.immas.org service: http://home-assistant.default.svc.cluster.local:8123`
The final catch-all rule must remain: `- service: http_status:404`

Auto-create DNS routes (no dashboard):
- To avoid manual DNS creation in Cloudflare, you can use the provided Job to route hostnames to the tunnel.
- Prerequisite: run `cloudflared login` locally once so `~/.cloudflared/cert.pem` exists.
- Then run one of:
   - `make tunnel-route-vault-dns` (routes `vault.immas.org`)
   - `make tunnel-route HOST=<hostname>` (routes any hostname)
- This will:
   - Create/refresh secret `cloudflared-origin-cert` from your local `cert.pem`.
   - Create ConfigMap `cloudflared-dns-route-params` with `TUNNEL_REF` (name or UUID) and `HOSTNAME`.
   - Apply `k8s/cloudflared/dns-route-job.yaml` which runs `cloudflared tunnel route dns $(TUNNEL_REF) $(HOSTNAME)`.
   - Print Job logs. Verify with `make verify-host HOST=<hostname>`.

Cleanup:
kubectl delete -f k8s/cloudflared/tunnel.yaml
