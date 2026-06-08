# qnfo-bootstrap — DeepChat Disaster Recovery

**~30-second recovery. ONE master prompt + 12 skills. Nothing else.**

## Quickstart (After Crash or Reset)

```powershell
# 1. Set your Cloudflare API token
setx CLOUDFLARE_API_TOKEN "your-token"

# 2. Run the bootstrap
python _quickstart_deepchat.py

# 3. DeepChat restarts automatically. Done.
```

## What This Repo Does

| File | Purpose |
|:-----|:--------|
| `_quickstart_deepchat.py` v4.0 | Deploy master prompt + 12 skills from R2, autonomous restart |
| `_r2_backup.py` | Python-based R2 upload (bypasses wrangler bug) |
| `_deploy.py` | Deploy skills from R2 (legacy, use quickstart instead) |
| `BOOTSTRAP.md` | Full disaster recovery guide |

## Architecture (v4.0 — Skill-Driven)

**Three things total. Nothing to drift. Nothing to sync.**

1. **Master prompt** — `app-settings.json.defaultSystemPrompt` (12KB, pulled from R2)
   - QNFO identity, policies, complete skill catalog, agent prompts inline
2. **12 QNFO skills** — `~/.deepchat/skills/` (plain markdown, individually deployable)
3. **Provider API key** — DeepChat Settings (must re-enter after reset)

**Dead and gone:** `custom_prompts.json`, `system_prompts.json`, agent prompt templates, rarely-used skills.

## See Also

- [BOOTSTRAP.md](BOOTSTRAP.md) — Complete disaster recovery guide
- [KNOWLEDGE-SETTINGS.md](KNOWLEDGE-SETTINGS.md) — Settings architecture reference (legacy)
