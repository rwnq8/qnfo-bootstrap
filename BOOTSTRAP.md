# QNFO DeepChat — Disaster Recovery Guide
## BOOTSTRAP.md v3.0 — 2026-06-08 — SKILL-DRIVEN ARCHITECTURE

> **AFTER A RESET OR CRASH:** This is all you need.
> **PRIMARY ENTRY POINT:** https://github.com/rwnq8/qnfo-bootstrap

### THE ARCHITECTURE (Three Things Only)

| # | What | Where | Survives Reset? |
|:--|:-----|:------|:----------------|
| 1 | **Master prompt** (12KB) | `app-settings.json.defaultSystemPrompt` | ✅ Pulled from R2 |
| 2 | **12 QNFO skills** | `~/.deepchat/skills/<name>/SKILL.md` | ✅ Individual markdown files |
| 3 | **Provider API key** | DeepChat Settings → Providers | ⚠️ Must re-enter |

**There is nothing else.** No `custom_prompts.json`. No `system_prompts.json`. No 27 prompt template JSON blobs. No triple-file sync traps. No version drift.

The master prompt contains: QNFO identity, all policies, complete skill catalog with trigger conditions, all 6 agent/subagent prompts inline. It's self-documenting — the agent knows everything it needs from this one file.

### QUICK RECOVERY (3 Steps, ~30 seconds)

```powershell
# 1. Set your API token (from password manager):
setx CLOUDFLARE_API_TOKEN "your-53-char-token"
# RESTART PowerShell

# 2. Run the bootstrap:
cd "G:\My Drive\qnfo-bootstrap"
python _quickstart_deepchat.py

# 3. DeepChat restarts automatically. Done.
```

### WHAT GETS RESTORED

| Asset | R2 Source | Size |
|:------|:----------|:-----|
| Master prompt | `qnfo/prompts/DEFAULT-SKILL-CATALOG.md` | ~12KB |
| execution-guard | `qnfo/prompts/skills/execution-guard/SKILL.md` | 4KB |
| qnfo-agent | `qnfo/prompts/skills/qnfo-agent/SKILL.md` | 117KB |
| cloudflare-deployer | `qnfo/prompts/skills/cloudflare-deployer/SKILL.md` | 9KB |
| publication-publisher | `qnfo/prompts/skills/publication-publisher/SKILL.md` | 25KB |
| closeout-manager | `qnfo/prompts/skills/closeout-manager/SKILL.md` | 15KB |
| git-hygiene | `qnfo/prompts/skills/git-hygiene/SKILL.md` | 5KB |
| pdf-builder | `qnfo/prompts/skills/pdf-builder/SKILL.md` | 15KB |
| email-composer | `qnfo/prompts/skills/email-composer/SKILL.md` | 5KB |
| knowledge-graph | `qnfo/prompts/skills/knowledge-graph/SKILL.md` | 15KB |
| prompt-audit | `qnfo/prompts/skills/prompt-audit/SKILL.md` | 13KB |
| local-to-r2-migration | `qnfo/prompts/skills/local-to-r2-migration/SKILL.md` | 27KB |
| kaizen-autonomous-update | `qnfo/prompts/skills/kaizen-autonomous-update/SKILL.md` | 6KB |

### WHAT WAS REMOVED (Dead Weight)

| Removed | Why |
|:--------|:----|
| `custom_prompts.json` | Duplicate of master — triple-file sync trap |
| `system_prompts.json` | Agent prompts now inline in master prompt |
| `acp_agents.json` | DeepChat manages internally |
| `projects-agent` skill | Was system prompt, not a skill |
| `prompts-agent` skill | Was system prompt, not a skill |
| `qwav-agent` skill | Was system prompt, not a skill |
| `explorer-subagent` skill | Was system prompt, not a skill |
| `implementer-subagent` skill | Was system prompt, not a skill |
| `reviewer-subagent` skill | Was system prompt, not a skill |
| `bling-usability-audit` skill | Rarely triggered |
| `template-catalog` skill | Moving away from templates |

### ARCHITECTURE COMPARISON

| | v2.x (OLD — Fragile) | v4.0 (NEW — Resilient) |
|:--|:---------------------|:------------------------|
| Files to sync | 7+ JSON files must agree | **1 master prompt + 12 skills** |
| System prompt size | 116KB embedded in JSON | 12KB self-documenting |
| Agent prompts | 7 separate JSON blobs | Inline in master prompt |
| Skills | 27+ (many never called) | 12 curated (all useful) |
| Version drift | 9 versions behind observed | Zero — master prompt IS canonical |
| Bootstrap failures | "Totally failed" for non-skill settings | Everything is a skill or the prompt |
| Restart | Manual | Autonomous |
| Time to recover | ~15 min | ~30 seconds |

### BOOTSTRAP CHAIN

```
github.com/rwnq8/qnfo-bootstrap  ← NO AUTH (public)
        ↓
  _quickstart_deepchat.py v4.0    ← pulls from R2
        ↓
  CLOUDFLARE_API_TOKEN            ← from password manager
        ↓
  R2: DEFAULT-SKILL-CATALOG.md    ← master prompt
  R2: prompts/skills/*/SKILL.md   ← 12 skills
        ↓
  DeepChat restarted              ← autonomous
```

### CRITICAL: Store Your Token

```
☐ Save API token in password manager
☐ Token also recoverable from Cloudflare Dashboard
```

### BOOTSTRAP RECOVERABILITY: 3/3 (100%)

All configuration is in 3 things: master prompt + 12 skills + API key. No JSON files to corrupt. No sync traps. No version drift.
