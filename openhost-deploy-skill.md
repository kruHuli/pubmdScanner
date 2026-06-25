# OpenHost Deploy — Claude Code Skill

A Claude Code custom slash command that walks you through deploying a Python web app to [OpenHost](https://github.com/imbue-openhost/openhost) (imbue's self-hosted compute platform), including secrets wiring via the cross-app services API.

Built from a real deployment session — every error below was hit in production.

---

## Install

Copy the skill file to your Claude Code commands directory:

```bash
mkdir -p ~/.claude/commands
curl -o ~/.claude/commands/deploy-openhost.md \
  https://raw.githubusercontent.com/kruHuli/pubmdScanner/main/linkedin-pipeline/openhost-deploy-skill.md
```

Or manually: copy the contents of the **Skill file** section below into `~/.claude/commands/deploy-openhost.md`.

Then in any Claude Code session, run:

```
/deploy-openhost
```

---

## What it does

Walks Claude through 10 steps:

| Step | What happens |
|---|---|
| 1 | Checks `oh` CLI is installed and you're logged in |
| 2 | Creates `requirements.txt` from your project imports |
| 3 | Creates a `Dockerfile` (Python 3.12-alpine + uv) |
| 4 | Creates `openhost.toml` with routing, resources, data, and secrets declaration |
| 5 | Adds `.gitignore` |
| 6 | Pushes to a public GitHub repo |
| 7 | Runs `oh app deploy` and handles common errors |
| 8 | Verifies the app is live |
| 9 | Wires up secrets via the cross-app services API (not env vars) |
| 10 | Shows how to redeploy after changes |

---

## Key things this skill knows that the docs don't say clearly

**Secrets are not auto-injected.**
The OpenHost Secrets dashboard stores your keys, but they never automatically become env vars in your container. You have to fetch them at request time via the cross-app services API:

```
POST {OPENHOST_ROUTER_URL}/api/services/v2/call/secrets/get
Authorization: Bearer {OPENHOST_APP_TOKEN}
{"keys": ["YOUR_KEY_NAME"]}
```

**You must declare the service in `openhost.toml`.**
Without `[[services.v2.consumes]]`, the router returns `shortname_not_declared` (404):

```toml
[[services.v2.consumes]]
service = "github.com/imbue-openhost/openhost/services/secrets"
shortname = "secrets"
version = ">=0.1.0"
grants = [
    {key = "YOUR_KEY_NAME"},
]
```

**First fetch returns a 403 with an approval URL.**
After adding the service declaration and deploying, the first request to the secrets API returns:
```json
{"error": "permission_required", "grant_url": "https://<zone>/approve-permissions-v2?..."}
```
Open that URL, approve, done. No redeploy needed.

**`oh instance login` must be run in a real terminal.**
It's interactive and will fail with an EOF error if run non-interactively (e.g. via `!` in Claude Code).

**The repo must be public.**
OpenHost clones from GitHub on deploy. Private repos cause `git clone failed`.

---

## Python helper function (copy into your app)

```python
import os, urllib.request, json
from pathlib import Path

def _get_secret(key: str) -> str:
    # 1. Local dev — direct env var
    if val := os.environ.get(key, ""):
        return val
    # 2. Manual fallback — file dropped via file-browser
    data_dir = os.environ.get("OPENHOST_APP_DATA_DIR", "")
    if data_dir:
        p = Path(data_dir) / f"{key.lower()}.txt"
        if p.exists():
            return p.read_text().strip()
    # 3. Production — cross-app services API
    router_url = os.environ.get("OPENHOST_ROUTER_URL", "")
    token      = os.environ.get("OPENHOST_APP_TOKEN", "")
    if router_url and token:
        try:
            body = json.dumps({"keys": [key]}).encode()
            req  = urllib.request.Request(
                f"{router_url}/api/services/v2/call/secrets/get",
                data=body,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                return json.loads(r.read()).get("secrets", {}).get(key, "")
        except Exception:
            pass
    return ""
```

---

## Debugging cheatsheet

| Symptom | Cause | Fix |
|---|---|---|
| `EOF` on `oh app deploy` | Not logged in | Run `oh instance login` in a real terminal |
| `git clone failed` | Private repo | Make the repo public on GitHub |
| HTML 500 instead of JSON | Flask crashes before responding | Wrap route in `try/except`, return `jsonify({"error": str(e)})` |
| `shortname_not_declared` (404) | Missing `[[services.v2.consumes]]` in `openhost.toml` | Add the block, redeploy |
| `permission_required` (403) | Grant not yet approved | Open the `grant_url` from the error response in your browser |
| Key still missing after approval | Key name mismatch | Check that the `key` in `grants` exactly matches what you're fetching |

---

## Skill file

Save this as `~/.claude/commands/deploy-openhost.md`:

```markdown
# Deploy app to OpenHost

You are helping the user deploy a web app to OpenHost (imbue self-hosted compute platform). Follow these steps exactly in order. Do not skip steps. Surface errors clearly before moving on.

## Step 1 — Prerequisites
Check `oh --version`. If missing: `uv tool install openhost-cli`.
Check `oh instance status`. If not logged in, tell the user to run `oh instance login` in their own terminal — it's interactive and won't work non-interactively.

## Step 2 — Create `requirements.txt`
Infer from project imports. Minimum for Flask: `flask>=3.0`.

## Step 3 — Create `Dockerfile`
FROM python:3.12-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "-u", "app.py"]

Ensure the entrypoint runs with host="0.0.0.0", port=8080.

## Step 4 — Create `openhost.toml`
[app]
name = "<app-name>"
version = "0.1.0"
description = "<description>"

[runtime.container]
image = "Dockerfile"
port = 8080

[routing]
health_check = "/"
public_paths = ["/"]

[[links]]
name = "Open App"
path = "/"

[resources]
memory_mb = 256
cpu_cores = 0.25

[data]
app_data = true

If the app uses secrets, also add:
[[services.v2.consumes]]
service = "github.com/imbue-openhost/openhost/services/secrets"
shortname = "secrets"
version = ">=0.1.0"
grants = [{key = "YOUR_SECRET_KEY_NAME"}]

## Step 5 — .gitignore
Add: __pycache__/, *.pyc, .env, *.db

## Step 6 — Push to public GitHub repo
OpenHost clones on deploy — repo must be public. `git push origin main`.

## Step 7 — Deploy
`oh app deploy` — prompts for git repo URL.
Common errors: `git clone failed` = private repo; `health check failed` = app crashing at startup.

## Step 8 — Verify
`oh app status <app-name>`. App live at https://<app-name>.<zone>/.

## Step 9 — Wire secrets
Secrets are NOT auto-injected as env vars. Fetch at request time:

router_url = os.environ.get("OPENHOST_ROUTER_URL", "")
token = os.environ.get("OPENHOST_APP_TOKEN", "")
body = json.dumps({"keys": ["YOUR_KEY"]}).encode()
req = urllib.request.Request(
    f"{router_url}/api/services/v2/call/secrets/get",
    data=body,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=5) as r:
    key = json.loads(r.read())["secrets"]["YOUR_KEY"]

First fetch returns HTTP 403 with a grant_url — tell user to open it in their browser and approve. No redeploy needed after approval.

## Step 10 — Redeploy after changes
Push to GitHub first, then: `oh app reload --update --wait <app-name>`

## Debugging
- HTML 500 instead of JSON: wrap routes in try/except, return jsonify({"error": str(e)})
- `oh app logs <app-name>` for container output
- Add `@app.route("/debug/env")` returning `jsonify({"env_keys": sorted(os.environ.keys())})` to inspect what the container sees
- OPENHOST_ROUTER_URL = http://host.containers.internal:8080 — reachable from inside the container
```
