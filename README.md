# qnfo-bootstrap — DeepChat Disaster Recovery

**One-command recovery for DeepChat settings, prompts, templates, skills, and configurations.**

If your machine crashed, you have a fresh Windows install, or DeepChat settings were corrupted — this repo has everything you need to restore.

## Quickstart (After Machine Crash)

```powershell
# Step 1: Install Node.js (if not already)
# Download from: https://nodejs.org

# Step 2: Set your Cloudflare API token
setx CLOUDFLARE_API_TOKEN "your-40-char-token"

# Step 3: Pull and run the quickstart
python _quickstart_deepchat.py

# Step 4: Restart DeepChat
```

**Recovery time: ~15 minutes** assuming you have your API token saved.

## What This Repo Contains

| File | Purpose |
|:-----|:--------|
| `_quickstart_deepchat.py` | Full DeepChat restore: prompts, configs, skills from R2 |
| `_r2_backup.py` | Python-based R2 upload/download (bypasses wrangler Windows bug) |
| `_deploy.py` | Deploy skills from R2 to DeepChat |
| `BOOTSTRAP.md` | Detailed disaster recovery guide with all scenarios |

## Prerequisites

- **Node.js** — https://nodejs.org (LTS version)
- **Python 3.10+** — https://python.org
- **Cloudflare API Token** — stored in your password manager (see below)
- **DeepSeek API Key** — retrieved from DeepSeek dashboard

## Creating Your Cloudflare API Token

1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token" → "Create Custom Token"
3. Configure:
   - **Token name:** "DeepChat R2 Access"
   - **Permissions:** Account → Cloudflare R2 Storage → Read
   - **Account Resources:** Include → quniverse
4. Copy the token and **STORE IT IN YOUR PASSWORD MANAGER**

## What Gets Restored

| Asset | Source |
|:------|:-------|
| 21 prompt templates | R2: `qnfo/prompts/prompts_bare.json` |
| 6 agent system prompts | R2: `qnfo/prompts/prompts_bare.json` |
| 12 QNFO skills | R2: `qnfo/prompts/skills/*/SKILL.md` |
| Model configurations | R2: `qnfo/deepchat/backup/model-config.json` |
| MCP server settings | R2: `qnfo/deepchat/backup/mcp-settings.json` |

## Bootstrap Chain

```
github.com/rwnq8/qnfo-bootstrap  ← NO AUTH NEEDED (public)
        ↓
  _quickstart_deepchat.py         ← clones or downloads
        ↓
  CLOUDFLARE_API_TOKEN            ← from password manager
        ↓
  R2 qnfo/  (all canonical data)  ← pulls everything
        ↓
  DeepChat restored               ← restart and go
```

## More Info

See [BOOTSTRAP.md](BOOTSTRAP.md) for the complete disaster recovery guide including:
- Full machine crash recovery
- Settings corruption fix
- API token loss recovery
- R2 bucket disaster recovery
