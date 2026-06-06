# QNFO DeepChat — Disaster Recovery Guide
## BOOTSTRAP.md v1.1 — 2026-06-06

> **PRIMARY RECOVERY ENTRY POINT:** https://github.com/rwnq8/qnfo-bootstrap
> 
> This GitHub repo is the FIRST place to go after a crash. It's public, requires no authentication, and contains everything needed to bootstrap back to full R2 access.

### THE ONE THING YOU NEED

After a complete machine crash or on a brand new computer, you need exactly **one** secret to restore everything:

> **Your Cloudflare API Token** (40-character string)

If you have this token, you can restore ALL DeepChat settings in ~15 minutes using the files from this GitHub repo.

### QUICK RECOVERY (Preferred — GitHub Bootstrap)

```powershell
# 1. Clone or download the bootstrap repo:
git clone https://github.com/rwnq8/qnfo-bootstrap.git
cd qnfo-bootstrap

# 2. Set your API token (from password manager):
setx CLOUDFLARE_API_TOKEN "your-40-char-token"
# RESTART PowerShell for env var to take effect

# 3. Run the quickstart:
python _quickstart_deepchat.py

# 4. Restart DeepChat
```

### ALTERNATIVE RECOVERY (If GitHub is inaccessible)

```powershell
# Pull quickstart directly from R2 (requires wrangler auth FIRST):
npx wrangler r2 object get qnfo/tools/quickstart_deepchat.py --remote --file=_qs.py
python _qs.py
```

#### Prerequisites
- [ ] Internet connection
- [ ] Cloudflare API token (see "Creating Your API Token" below)

#### Step 1: Install Node.js
```
Download: https://nodejs.org
Install: LTS version (includes npm)
Verify:  node --version
```

#### Step 2: Install DeepChat
```
Download DeepChat from your app store or website
Install and launch once (to create the AppData directory)
Then CLOSE DeepChat (it must be closed during restore)
```

#### Step 3: Set Cloudflare API Token
```powershell
# In PowerShell (as regular user):
setx CLOUDFLARE_API_TOKEN "your-40-character-token-here"

# RESTART PowerShell for the variable to take effect
# Verify:
npx wrangler whoami
# Should show: "You are logged in with an Account API Token"
```

#### Step 4: Pull and Run Quickstart
```powershell
# Pull the recovery script from R2:
npx wrangler r2 object get qnfo/tools/quickstart_deepchat.py --remote --file=_qs.py

# Run it:
python _qs.py

# This restores:
#   - All 21 prompt templates
#   - All 6 system prompts
#   - All 12 QNFO skills
#   - Model configurations
#   - MCP server settings
```

#### Step 5: Configure DeepSeek API Key
```
Open DeepChat → Settings → Providers
Add your DeepSeek API key
Restart DeepChat
```

#### Step 6: Verify
```
DeepChat Settings → Prompts → you should see 21 templates
DeepChat Settings → System Prompts → you should see 6 agents
Try sending a message — it should work
```

---

### LIGHTER RECOVERY SCENARIOS

#### DeepChat Settings Corrupted (Token Still Local)
```powershell
npx wrangler r2 object get qnfo/tools/quickstart_deepchat.py --remote --file=_qs.py
python _qs.py --prompts-only
# Restart DeepChat
```

#### Only Skills Missing
```powershell
npx wrangler r2 object get qnfo/tools/quickstart_deepchat.py --remote --file=_qs.py
python _qs.py --skills-only
```

#### Only Configs Missing
```powershell
npx wrangler r2 object get qnfo/tools/quickstart_deepchat.py --remote --file=_qs.py
python _qs.py --configs-only
```

---

### CREATING YOUR API TOKEN

```
1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Select "Create Custom Token"
4. Configure:
   - Token name: "DeepChat R2 Access"
   - Permissions: Account → Cloudflare R2 Storage → Read
   - Account Resources: Include → quniverse
5. Click "Continue to summary" → "Create Token"
6. COPY THE TOKEN IMMEDIATELY (it won't be shown again)
7. Store it in your password manager
```

---

### CRITICAL: Store Your Token BEFORE Disaster

```
☐ Save API token in password manager (Bitwarden, 1Password, etc.)
☐ Print a physical copy (keep in secure location)
☐ The token is also always recoverable from Cloudflare Dashboard
  (requires Cloudflare email + password + 2FA if enabled)
```

---

### WHAT SURVIVES ON R2

| Asset | R2 Path | Status |
|:------|:--------|:-------|
| All prompt templates (21) | `qnfo/prompts/prompts_bare.json` | ✅ Backed up |
| All system prompts (6) | `qnfo/prompts/prompts_bare.json` | ✅ Backed up |
| All skills (12) | `qnfo/prompts/skills/*/SKILL.md` | ✅ Backed up |
| DEFAULT.md | `qnfo/prompts/DEFAULT.md` | ✅ Backed up |
| QWAV-DEFAULT.md | `qnfo/prompts/QWAV-DEFAULT.md` | ✅ Backed up |
| META-PROMPT | `qnfo/prompts/META-PROMPT-DEEPSEEK.md` | ✅ Backed up |
| Quickstart script | `qnfo/tools/quickstart_deepchat.py` | ✅ Backed up |
| Deploy script | `qnfo/tools/deploy.py` | ✅ Backed up |
| Model configs | `qnfo/deepchat/backup/model-config.json` | ⚠️ May be stale |
| MCP settings | `qnfo/deepchat/backup/mcp-settings.json` | ⚠️ May be stale |
| Discovery Index | `qnfo/discovery/index.json` | ✅ Backed up |

### WHAT DOES NOT SURVIVE ON R2

- DeepSeek API key (stored encrypted in DeepChat — recoverable from DeepSeek dashboard)
- Session/conversation history (stored locally only)
- Cloudflare API token itself (the KEY to everything — store separately!)

---

### BOOTSTRAP RECOVERABILITY: 3/12 (25%) → TARGET 8/12 (67%)

Current score is LOW because config files (model-config.json, mcp-settings.json) are not reliably backed up to R2 due to a wrangler Windows bug. Fix: use Python-based Cloudflare API for uploads instead of wrangler CLI.

**This document itself is stored at:** `qnfo/discovery/BOOTSTRAP.md` on R2
**Public URL (planned):** `https://deep.qwav.tech/bootstrap`
