# Shell Commands Reference

A quick reference for common shell patterns used in log inspection and command-line operations.

## Redirection Operators

### `2>&1` - Redirect stderr to stdout
- `2` = stderr (error messages)
- `1` = stdout (normal output)
- `&` = reference to a file descriptor
- **Example:** `curl -sv https://home.immas.org 2>&1` merges errors into output so you can pipe them

### `>` vs `>>`
- `>` - Overwrite file
  ```bash
  echo "new content" > file.txt
  ```
- `>>` - Append to file
  ```bash
  echo "additional line" >> file.txt
  ```

## Filtering Commands

### `tail` - Show last N lines
```bash
kubectl logs deploy/cloudflared --tail=20  # Get last 20 log lines
tail -50 /var/log/syslog                   # Last 50 lines of a file
tail -f /var/log/syslog                    # Follow file in real-time
```

### `head` - Show first N lines
```bash
curl -sv https://home.immas.org 2>&1 | head -20  # First 20 lines of output
head -10 file.txt                                # First 10 lines of file
```

### Combining `tail` and `head`
```bash
kubectl logs deploy/cloudflared --tail=50 | head -10
# Gets last 50 lines, then shows first 10 of those
# Result: lines 41-50 from the end
```

## grep - Pattern Matching

### Basic grep
```bash
kubectl logs deploy/cloudflared | grep "tunnel"
# Show only lines containing "tunnel"
```

### Case-insensitive search
```bash
kubectl logs deploy/cloudflared | grep -i error
# Show lines with "error", "Error", "ERROR", etc.
```

### Extended regex (multiple patterns)
```bash
kubectl logs deploy/cloudflared | grep -E "(tunnel|error|config)"
# Show lines containing "tunnel" OR "error" OR "config"
```

### Invert match (exclude lines)
```bash
kubectl logs deploy/cloudflared | grep -v "INF"
# Hide lines containing "INF" (informational messages)
```

### Context lines
```bash
kubectl logs deploy/cloudflared | grep -A3 -B3 "error"
# Show 3 lines After and 3 lines Before each match
```

### Count matches
```bash
kubectl logs deploy/cloudflared | grep -c "Registered tunnel"
# Count how many times pattern appears
```

### Show only matching part
```bash
echo "IP: 192.168.1.100" | grep -o "[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+"
# Output: 192.168.1.100
```

## Useful Combinations

### Show errors only
```bash
kubectl logs deploy/cloudflared 2>&1 | grep -i error
```

### Last 100 lines, filter for specific pattern
```bash
kubectl logs deploy/cloudflared --tail=100 | grep "Updated to new configuration"
```

### Multiple filters chained
```bash
kubectl logs deploy/cloudflared | grep "tunnel" | grep -v "connection" | head -20
# Show tunnel logs, exclude "connection", show first 20
```

### Save filtered output to file
```bash
kubectl logs deploy/cloudflared | grep error > errors.log
```

### Search across multiple files
```bash
grep -r "TODO" k8s/manifests/
# Recursively search for "TODO" in all files under k8s/manifests/
```

## Advanced Patterns

### Using awk for column extraction
```bash
kubectl get pods -A | awk '{print $1, $2}'
# Print first two columns (namespace and pod name)
```

### Using sed for text replacement
```bash
echo "hello world" | sed 's/world/universe/'
# Output: hello universe
```

### Combine multiple commands
```bash
kubectl logs deploy/cloudflared --tail=100 | \
  grep -E "(error|warning)" | \
  grep -v "connection" | \
  sort | uniq
# Get last 100 lines, show errors/warnings, exclude "connection", sort and deduplicate
```

### Real-time log following with filtering
```bash
kubectl logs -f deploy/cloudflared | grep --line-buffered "error"
# Follow logs in real-time, show only error lines
```

## File Descriptors Reference

- `0` = stdin (standard input)
- `1` = stdout (standard output)
- `2` = stderr (standard error)

### Common redirections
```bash
command > output.txt 2>&1           # Redirect both stdout and stderr to file
command 2> errors.txt               # Redirect only stderr to file
command > /dev/null 2>&1            # Discard all output (silence command)
command 2>&1 | tee output.txt       # Show output AND save to file
```

## Tips

1. **Use `--color=always` with grep in pipes:**
   ```bash
   kubectl logs deploy/cloudflared | grep --color=always "error" | less -R
   ```

2. **Use `less` for paginated output:**
   ```bash
   kubectl logs deploy/cloudflared | less
   # Navigate with arrow keys, search with /, quit with q
   ```

3. **Combine with watch for periodic updates:**
   ```bash
   watch -n 2 'kubectl get pods -A | grep -v Running'
   # Every 2 seconds, show non-Running pods
   ```

4. **Use `xargs` to process lines:**
   ```bash
   kubectl get pods -o name | xargs -I {} kubectl delete {}
   # Delete all pods (careful!)
   ```
