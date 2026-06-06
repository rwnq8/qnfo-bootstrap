# DeepChat Settings Architecture — Canonical Reference
## KNOWLEDGE-SETTINGS.md v1.0 — 2026-06-06

> **DO NOT LOSE THIS KNOWLEDGE.** This document captures everything learned about DeepChat's settings storage, programmatic update mechanisms, and bootstrap recovery. Read this BEFORE making any prompt or settings changes.

---

## 1. THE THREE-FILE ARCHITECTURE

DeepChat stores prompts and settings across THREE separate JSON files. **ALL THREE must be updated** for changes to take effect. Updating only one or two will result in invisible changes or reversion.

| File | Role | Location | Contents |
|:------|:-----|:---------|:---------|
| **`app-settings.json`** | 🔑 MASTER CONFIG | `%APPDATA%\DeepChat\` | `defaultSystemPrompt` (active agent prompt, ~71KB), `promptTemplates` (all templates+agents), `preferredModel`, all app settings |
| **`custom_prompts.json`** | Prompt Templates | `%APPDATA%\DeepChat\` | `{"prompts": [...]}` — 21 template entries |
| **`system_prompts.json`** | Agent System Prompts | `%APPDATA%\DeepChat\` | `{"prompts": [...]}` — 6 agent entries (PROJECTS, PROMPTS, QWAV, EXPLORER, IMPLEMENTER, REVIEWER) |

### File Relationships (Critical!)

```
app-settings.json (MASTER)
├── promptTemplates: [27 items] ← ALL templates + ALL system prompts
│   ├── 18 templates (duplicated in custom_prompts.json)
│   ├── 6 system prompts (duplicated in system_prompts.json)
│   ├── 3 templates (ONLY here: DEEP-DIVE-DISCOVERY, HTML-PUBLICATION-PAGE, MATHJAX-CONFIG)
│   └── 1 stale entry (PDF-BUILDER — delete this)
├── defaultSystemPrompt: "full DEFAULT.md text" ← THE ACTIVE PROMPT
├── default_system_prompt: (DEPRECATED — remove this, 62KB bloat)
└── preferredModel: {providerId, modelId}

custom_prompts.json (IMPORT/EXPORT)
└── prompts: [21 template entries]
    └── 18 duplicated in app-settings.promptTemplates

system_prompts.json (IMPORT/EXPORT)
└── prompts: [6 agent entries]
    └── ALL 6 duplicated in app-settings.promptTemplates
```

**Key insight:** `app-settings.json` is the MASTER. DeepChat reads this file on startup. `custom_prompts.json` and `system_prompts.json` are import/export surfaces. If you write to custom_prompts.json but NOT app-settings.json, the changes won't appear in the UI.

---

## 2. PROGRAMMATIC UPDATE PROCEDURE

### Step 1: TERMINATE DEEPCHAT

```powershell
# CRITICAL: DeepChat must be COMPLETELY CLOSED before any writes.
# It holds file locks and may revert changes on shutdown.
taskkill /f /im DeepChat.exe 2>$null
# Verify it's dead:
Get-Process DeepChat -ErrorAction SilentlyContinue  # should return nothing
```

### Step 2: Update All Three Files

```python
import json, os
from pathlib import Path

dc = Path(os.environ['APPDATA']) / 'DeepChat'

# 1. Update app-settings.json (MASTER — most important)
with open(dc / 'app-settings.json', encoding='utf-8') as f:
    app = json.load(f)

# Replace the active system prompt:
with open('DEFAULT.md', encoding='utf-8') as f:
    app['defaultSystemPrompt'] = f.read()

# Remove deprecated key (saves 62KB):
app.pop('default_system_prompt', None)

# Sync promptTemplates:
# app['promptTemplates'] = all_27_entries_from_R2

with open(dc / 'app-settings.json', 'w', encoding='utf-8') as f:
    json.dump(app, f, indent=2, ensure_ascii=False)

# 2. Update custom_prompts.json
with open(dc / 'custom_prompts.json', 'w', encoding='utf-8') as f:
    json.dump({"prompts": template_entries}, f, indent=2, ensure_ascii=False)

# 3. Update system_prompts.json
with open(dc / 'system_prompts.json', 'w', encoding='utf-8') as f:
    json.dump({"prompts": agent_entries}, f, indent=2, ensure_ascii=False)
```

### Step 3: Verify Before Restart

```python
# Verify all three files have correct content
# Check version numbers match R2 canonical
```

### Step 4: Restart DeepChat

Changes take effect on next launch. DeepChat reads all three files on startup.

---

## 3. VERSION DRIFT DETECTION

DeepChat's `app-settings.json` embeds the FULL system prompt text in `defaultSystemPrompt`. This text DRIFTS from the R2 canonical source over time because DeepChat only reads it on first import.

**Detection:**
```python
import re, json
# Check active version
m = re.search(r'v(\d+\.\d+)', app['defaultSystemPrompt'][:500])
active_ver = m.group(1) if m else '?'

# Compare with R2 canonical
# If active_ver != r2_ver → DRIFT DETECTED → needs update
```

**Historical drift observed:**
- 2026-06-06: Active was v3.18, R2 canonical was v3.27 (9 versions behind!)
- Fix: Manual update via `_quickstart_deepchat.py --app-settings-only`

---

## 4. CANONICAL SOURCE HIERARCHY

```
R2 (qnfo/prompts/)              ← SINGLE SOURCE OF TRUTH
├── DEFAULT.md                  ← Canonical system prompt (v3.27+)
├── QWAV-DEFAULT.md             ← QWAV agent prompt
├── META-PROMPT-DEEPSEEK.md     ← Prompt generator prompt
├── prompts_bare.json           ← All 27 entries (bare array, import format)
├── prompts.json                ← All 27 entries (wrapped format)
└── templates/*.md              ← Individual template source files
    └── skills/*/SKILL.md       ← All 12 skill definitions

GitHub (rwnq8/qnfo-bootstrap)   ← DISASTER RECOVERY ENTRY POINT
├── _quickstart_deepchat.py     ← One-click full restore
├── _r2_backup.py               ← Python-based R2 upload (bypasses wrangler bug)
├── _deploy.py                  ← Skill deployment from R2
├── BOOTSTRAP.md                ← Complete recovery guide
└── README.md                   ← Quickstart instructions

DeepChat AppData (%APPDATA%\DeepChat\)  ← EPHEMERAL RUNTIME
├── app-settings.json           ← Master config (rebuilt from R2 on recovery)
├── custom_prompts.json         ← Templates (rebuilt from R2)
├── system_prompts.json         ← Agent prompts (rebuilt from R2)
├── model-config.json           ← Model settings (backed up to R2)
└── mcp-settings.json           ← MCP servers (backed up to R2)
```

---

## 5. RECOVERY TOOLS & THEIR ROLES

| Tool | Location | Purpose |
|:------|:---------|:--------|
| `_quickstart_deepchat.py` v2.1 | R2 `qnfo/tools/`, GitHub | Full restore: prompts + configs + skills + app-settings |
| `_r2_backup.py` v1.1 | R2 `qnfo/tools/`, GitHub | Python-based R2 upload (bypasses wrangler Windows bug) |
| `_deploy.py` v3.0 | R2 `qnfo/tools/`, GitHub | Deploy skills from R2 to DeepChat |
| `BOOTSTRAP.md` v1.1 | R2 `qnfo/discovery/`, GitHub | Complete disaster recovery guide |
| `KNOWLEDGE-SETTINGS.md` | R2, GitHub | THIS DOCUMENT — settings architecture reference |

---

## 6. KEY LESSONS LEARNED

1. **Three files, not one.** Writing to `custom_prompts.json` alone is invisible. You MUST update `app-settings.json.promptTemplates` too.

2. **app-settings.json is the master.** DeepChat reads this on startup. The other two files are secondary import/export surfaces.

3. **Terminate DeepChat before writes.** The app holds file locks and may revert changes on shutdown. `taskkill /f /im DeepChat.exe` before any programmatic update.

4. **Version drift is real.** The embedded `defaultSystemPrompt` can fall 9+ versions behind R2 canonical. Check for drift regularly.

5. **The stale `default_system_prompt` key** (v3.13, 62KB) should always be removed. It's deprecated bloat that DeepChat may recreate as empty on restart.

6. **Wrangler Windows bug** (UV_HANDLE_CLOSING assertion) blocks uploads. Use `_r2_backup.py` (Python direct API) as fallback.

7. **28 unique prompt names** exist across three files with significant duplication. Don't create new duplicates — update existing entries.

8. **The bootstrap chain:** GitHub (no auth) → quickstart script → R2 (with API token) → full DeepChat restore. The API token is the single point of failure.

---

## 7. QUICK REFERENCE: COMMANDS

```powershell
# Kill DeepChat (MANDATORY before any programmatic update)
taskkill /f /im DeepChat.exe

# Restore everything from R2
python _quickstart_deepchat.py

# Restore only prompts
python _quickstart_deepchat.py --prompts-only

# Restore only app-settings (fix version drift)
python _quickstart_deepchat.py --app-settings-only

# Backup current state to R2
python _quickstart_deepchat.py --backup-now

# Deploy skills from R2
python _deploy.py --skills-only

# Upload files to R2 (bypasses wrangler bug)
python _r2_backup.py upload local_file.txt qnfo/path/on/r2
python _r2_backup.py --batch manifest.json

# Check for version drift
python -c "import json,re,os; app=json.load(open(os.path.join(os.environ['APPDATA'],'DeepChat','app-settings.json'),encoding='utf-8')); m=re.search(r'v(\d+\.\d+)',app.get('defaultSystemPrompt','')[:500]); print(f'Active: v{m.group(1) if m else \"?\"}')"
```

---

## 8. WHEN UPDATING SYSTEM PROMPTS

Follow this checklist EVERY time:

- [ ] 1. **TERMINATE DeepChat** (`taskkill /f /im DeepChat.exe`)
- [ ] 2. Update R2 canonical: `qnfo/prompts/DEFAULT.md`, `META-PROMPT-DEEPSEEK.md`, `QWAV-DEFAULT.md`
- [ ] 3. Rebuild `prompts_bare.json` and `prompts.json` on R2
- [ ] 4. Update template source files on R2: `qnfo/prompts/templates/*.md`
- [ ] 5. Update skill SKILL.md files on R2 if needed
- [ ] 6. Run: `python _quickstart_deepchat.py --app-settings-only` (updates all three DeepChat files)
- [ ] 7. Run: `python _quickstart_deepchat.py --prompts-only` (refreshes templates)
- [ ] 8. **Restart DeepChat**
- [ ] 9. Verify: check `app-settings.json` → `defaultSystemPrompt` version matches R2
- [ ] 10. Push updated quickstart to GitHub: `rwnq8/qnfo-bootstrap`
- [ ] 11. Update R2 backups: `_quickstart_deepchat.py --backup-now`
- [ ] 12. Run: `python _deploy.py --skills-only` (if skills changed)
