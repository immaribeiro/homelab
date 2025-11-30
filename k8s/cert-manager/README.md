cert-manager setup (DNS-01 via Cloudflare)

Steps:
- Install cert-manager:
  - `kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml`
- Create API token secret (env var required):
  - `export CLOUDFLARE_API_TOKEN=...`
  - `kubectl create namespace cert-manager --dry-run=client -o yaml | kubectl apply -f -`
  - `kubectl -n cert-manager create secret generic cloudflare-api-token-secret --from-literal=api-token="$CLOUDFLARE_API_TOKEN"`
- Apply issuers:
  - Edit `k8s/cert-manager/clusterissuers.yaml` and set your email address.
  - `kubectl apply -f k8s/cert-manager/clusterissuers.yaml`

Notes:
- DNS-01 works without exposing your services publicly; only Cloudflare DNS is needed.
- Use `letsencrypt-staging` during testing to avoid rate limits, then switch to `letsencrypt-prod`.
