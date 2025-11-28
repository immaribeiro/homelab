# !/bin/sh

-lc 'set -euo pipefail
echo "Checking environment..."
PYTHON=$(command -v python3 || true)
PIP=$(command -v pip3 || true)
YAMLLINT=$(command -v yamllint || true)
ANSIBLE_LINT=$(command -v ansible-lint || true)
KUBECTL=$(command -v kubectl || true)

if [ -z "$PYTHON" ] || [ -z "$PIP" ]; then
  echo "python3 or pip3 not found. Please install Python 3 and pip3 (Homebrew: brew install python)" >&2
fi
#!/usr/bin/env bash
set -euo pipefail

echo "Checking environment..."
PYTHON=$(command -v python3 || true)
PIP=$(command -v pip3 || true)
YAMLLINT=$(command -v yamllint || true)
ANSIBLE_LINT=$(command -v ansible-lint || true)
KUBECTL=$(command -v kubectl || true)

if [ -z "$PYTHON" ] || [ -z "$PIP" ]; then
  echo "python3 or pip3 not found. Please install Python 3 and pip3 (Homebrew: brew install python)" >&2
fi

# Install yamllint if missing
if [ -z "$YAMLLINT" ]; then
  echo "yamllint not found — installing via pip3 --user..."
  pip3 install --user yamllint || { echo "Failed to install yamllint" >&2; exit 1; }
  export PATH="$HOME/.local/bin:$PATH"
  YAMLLINT=$(command -v yamllint)
fi

# Install ansible-lint if missing
if [ -z "$ANSIBLE_LINT" ]; then
  echo "ansible-lint not found — installing via pip3 --user..."
  pip3 install --user ansible-lint || { echo "Failed to install ansible-lint" >&2; exit 1; }
  export PATH="$HOME/.local/bin:$PATH"
  #!/usr/bin/env bash
  set -euo pipefail

  echo "Checking environment..."
  PYTHON=$(command -v python3 || true)
  PIP=$(command -v pip3 || true)
  YAMLLINT=$(command -v yamllint || true)
  ANSIBLE_LINT=$(command -v ansible-lint || true)
  KUBECTL=$(command -v kubectl || true)

  if [ -z "${PYTHON}" ] || [ -z "${PIP}" ]; then
    echo "python3 or pip3 not found. Please install Python 3 and pip3 (Homebrew: brew install python)" >&2
  fi

  # Ensure ~/.local/bin is on PATH for --user installs
  export PATH="$HOME/.local/bin:$PATH"

  # Install yamllint if missing
  if [ -z "${YAMLLINT}" ]; then
    echo "yamllint not found — installing via pip3 --user..."
    pip3 install --user yamllint || { echo "Failed to install yamllint" >&2; exit 1; }
    YAMLLINT=$(command -v yamllint || true)
  fi

  # Install ansible-lint if missing
  if [ -z "${ANSIBLE_LINT}" ]; then
    echo "ansible-lint not found — installing via pip3 --user..."
    pip3 install --user ansible-lint || { echo "Failed to install ansible-lint" >&2; exit 1; }
    ANSIBLE_LINT=$(command -v ansible-lint || true)
  fi

  echo "Using yamllint: ${YAMLLINT:-not found}"
  echo "Using ansible-lint: ${ANSIBLE_LINT:-not found}"
  echo "Using kubectl: ${KUBECTL:-not found}"

  # Run yamllint on common YAML locations
  echo
  echo "Running yamllint..."
  # collect files
  FILES=()
  for pattern in ansible/*.yml ansible/playbooks/*.yml ansible/group_vars/*.yml lima/templates/*.yaml k8s/manifests/*.yml; do
    for f in $pattern; do
      [ -f "$f" ] || continue
      FILES+=("$f")
    done
  done

  if [ ${#FILES[@]} -eq 0 ]; then
    echo "No YAML files found for yamllint."
  else
    if [ -n "${YAMLLINT}" ]; then
      "${YAMLLINT}" "${FILES[@]}" || true
    else
      echo "yamllint not available; skipping yamllint run."
    fi
  fi

  # Run ansible-lint on playbooks
  echo
  echo "Running ansible-lint..."
  EXIST=0
  for p in ansible/playbooks/*.yml; do
    [ -f "$p" ] && EXIST=1 || true
  done
  if [ $EXIST -eq 1 ]; then
    if [ -n "${ANSIBLE_LINT}" ]; then
      "${ANSIBLE_LINT}" ansible/playbooks || true
    else
      echo "ansible-lint not available; skipping ansible-lint run."
    fi
  else
    echo "No playbooks found for ansible-lint."
  fi

  # Try kubectl dry-run validation for k8s manifests
  if [ -n "${KUBECTL}" ]; then
    echo
    echo "Running kubectl --dry-run=client to validate k8s manifests..."
    for m in k8s/manifests/*.yml; do
      [ -f "$m" ] || continue
      echo "Validating $m"
      kubectl apply --dry-run=client -f "$m" || true
    done
  else
    echo
    echo "kubectl not found — skipping k8s manifest validation. Install kubectl to enable this check."
  fi

  echo
  echo "Linters run complete. Summary:"
  if [ -n "${YAMLLINT}" ]; then echo "- yamllint ran on ${#FILES[@]} file(s)"; fi
  if [ -n "${ANSIBLE_LINT}" ]; then echo "- ansible-lint ran (see output above)"; fi
  if [ -n "${KUBECTL}" ]; then echo "- kubectl dry-run validations attempted"; else echo "- kubectl validation skipped"; fi'
