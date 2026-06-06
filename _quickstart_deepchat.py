#!/usr/bin/env python3
"""
_quickstart_deepchat.py v2.2 — FULL DeepChat restoration from R2.

Usage:
    python _quickstart_deepchat.py [--dry-run]
    python _quickstart_deepchat.py --prompts-only
    python _quickstart_deepchat.py --configs-only
    python _quickstart_deepchat.py --skills-only

PREREQUISITES (one-time):
    1. Node.js installed (https://nodejs.org)
    2. Cloudflare API token set: setx CLOUDFLARE_API_TOKEN "your-token"
       (Token needs R2 Read access on the 'qnfo' bucket)

RESTORES:
    - custom_prompts.json (21 prompt templates)
    - system_prompts.json (6 agent system prompts)
    - model-config.json (4 DeepSeek model configurations)
    - mcp-settings.json (13 MCP servers)
    - acp_agents.json (agent configuration)
    - knowledge-configs.json (knowledge base configs)
    - ALL skills (from qnfo/prompts/skills/ to %USERPROFILE%/.deepchat/skills/)

CANONICAL SOURCE: Cloudflare R2 bucket 'qnfo', prefix 'qnfo/'
TARGET: %APPDATA%/DeepChat/ (or %USERPROFILE%/.deepchat/ for skills)

This script is IDEMPOTENT — safe to run multiple times.
"""
import json, os, subprocess, sys, shutil, argparse
from pathlib import Path

R2_BUCKET = "qnfo"

# === DETECT DEEPCHAT DIRECTORIES ===
SKILLS_DIR = Path.home() / ".deepchat" / "skills"
if not SKILLS_DIR.parent.exists():
    APPDATA = Path(os.environ.get("APPDATA", os.path.expandvars(r"%APPDATA%")))
    DEEPCHAT_DIR = APPDATA / "DeepChat"
else:
    DEEPCHAT_DIR = Path.home() / ".deepchat"
    # But custom_prompts.json is in AppData
    APPDATA = Path(os.environ.get("APPDATA", os.path.expandvars(r"%APPDATA%")))
    DEEPCHAT_DIR = APPDATA / "DeepChat"

SKILLS_DIR = Path.home() / ".deepchat" / "skills"

# === HELPERS ===
def run(cmd, desc=""):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        ok = r.returncode == 0
        if not ok:
            print(f"  FAIL: {desc}: {r.stderr.strip()[:200]}")
        return ok, r.stdout.strip()
    except Exception as e:
        print(f"  ERROR: {desc}: {e}")
        return False, ""

def r2_pull(remote_path, local_path, desc=""):
    """Pull a file from R2."""
    ok, _ = run(
        f'npx wrangler r2 object get {R2_BUCKET}/{remote_path} --remote --file="{local_path}"',
        desc or f"Pull {remote_path}"
    )
    return ok and Path(local_path).exists()

def backup_existing(filepath):
    """Backup an existing file before overwriting."""
    if filepath.exists():
        bak = Path(str(filepath) + ".bak")
        shutil.copy2(filepath, bak)
        return True
    return False

def r2_upload(local_path, remote_path):
    """Upload a file to R2."""
    ok, _ = run(
        f'npx wrangler r2 object put {R2_BUCKET}/{remote_path} --file="{local_path}" --remote',
        f"Upload {remote_path}"
    )
    return ok

# === RESTORE PROMPTS ===
def restore_prompts(dry_run=False):
    """Restore prompt templates and system prompts from R2."""
    print("\n" + "=" * 60)
    print("RESTORE: Prompt Templates & System Prompts")
    print("=" * 60)
    
    local = Path("_tmp_prompts_bare.json")
    if not r2_pull("prompts/prompts_bare.json", str(local), "Pull prompts manifest"):
        print("CRITICAL: Cannot pull prompts_bare.json from R2.")
        print("  Check: CLOUDFLARE_API_TOKEN is set and has R2 read access to bucket 'qnfo'.")
        return False
    
    with open(local, encoding='utf-8') as f:
        all_entries = json.load(f)
    
    agent_names = {'PROJECTS-AGENT', 'PROMPTS-AGENT', 'QWAV-AGENT',
                   'EXPLORER-SUBAGENT', 'IMPLEMENTER-SUBAGENT', 'REVIEWER-SUBAGENT'}
    templates = [e for e in all_entries if e.get('name', '') not in agent_names]
    system_prompts = [e for e in all_entries if e.get('name', '') in agent_names]
    
    print(f"  Source: {len(all_entries)} total entries")
    print(f"  Templates: {len(templates)}, System prompts: {len(system_prompts)}")
    
    if dry_run:
        print("\n  [DRY RUN] Would restore to:")
        print(f"    {DEEPCHAT_DIR / 'custom_prompts.json'}")
        print(f"    {DEEPCHAT_DIR / 'system_prompts.json'}")
    else:
        for fname, data in [('custom_prompts.json', templates), 
                            ('system_prompts.json', system_prompts)]:
            target = DEEPCHAT_DIR / fname
            if target.exists():
                backup_existing(target)
            with open(target, 'w', encoding='utf-8') as f:
                json.dump({"prompts": data}, f, indent=2, ensure_ascii=False)
            print(f"  RESTORED: {fname} ({len(data)} entries)")
    
    local.unlink(missing_ok=True)
    return True

# === RESTORE CONFIGS ===
CONFIG_MAP = {
    "model-config.json": "qnfo/deepchat/backup/model-config.json",
    "mcp-settings.json": "qnfo/deepchat/backup/mcp-settings.json",
    "acp_agents.json": "qnfo/deepchat/backup/acp_agents.json",
    "knowledge-configs.json": "qnfo/deepchat/backup/knowledge-configs.json",
}

def restore_configs(dry_run=False):
    """Restore DeepChat configuration files from R2 backups."""
    print("\n" + "=" * 60)
    print("RESTORE: Configuration Files")
    print("=" * 60)
    
    results = {}
    for fname, r2_path in CONFIG_MAP.items():
        local_tmp = Path(f"_tmp_{fname}")
        target = DEEPCHAT_DIR / fname
        
        if not r2_pull(r2_path, str(local_tmp), f"Pull {fname} backup"):
            print(f"  WARN: {fname} — not available on R2 (will skip)")
            results[fname] = "SKIPPED (not on R2)"
            continue
        
        with open(local_tmp, encoding='utf-8') as f:
            data = json.load(f)
        
        if dry_run:
            print(f"  [DRY RUN] Would restore {fname} ({len(json.dumps(data))} bytes)")
            results[fname] = "WOULD_RESTORE"
        else:
            if target.exists():
                backup_existing(target)
            with open(target, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  RESTORED: {fname}")
            results[fname] = "RESTORED"
        
        local_tmp.unlink(missing_ok=True)
    
    return results

# === RESTORE APP SETTINGS ===
def restore_app_settings(dry_run=False):
    """Update app-settings.json with latest R2 canonical prompts.

    This is the MOST IMPORTANT step — DeepChat reads app-settings.json
    as its master config file. Without this, restored templates may not
    appear in the DeepChat UI.
    """
    print("\n" + "=" * 60)
    print("RESTORE: App Settings (Master Config)")
    print("=" * 60)

    ap_path = DEEPCHAT_DIR / 'app-settings.json'
    if not ap_path.exists():
        print("  WARN: app-settings.json not found (fresh install?)")
        return {"app-settings": "SKIPPED (not found)"}

    # Pull latest DEFAULT.md from R2
    default_tmp = Path("_tmp_default_latest.md")
    if not r2_pull("prompts/DEFAULT.md", str(default_tmp), "Pull latest DEFAULT.md"):
        print("  WARN: Cannot pull DEFAULT.md from R2")
        return {"app-settings": "SKIPPED (no DEFAULT.md on R2)"}

    with open(default_tmp, encoding='utf-8') as f:
        latest_default = f.read()

    # Pull prompts_bare.json from R2 for template sync
    prompts_tmp = Path("_tmp_prompts_bare.json")
    if not r2_pull("prompts/prompts_bare.json", str(prompts_tmp), "Pull prompts manifest"):
        return {"app-settings": "SKIPPED (no prompts_bare.json on R2)"}

    with open(prompts_tmp, encoding='utf-8') as f:
        all_entries = json.load(f)

    # Read current app-settings
    with open(ap_path, encoding='utf-8') as f:
        app = json.load(f)

    results = {}
    import re

    # 1. Update defaultSystemPrompt (the active agent prompt)
    old_ver = '?'
    if app.get('defaultSystemPrompt'):
        m = re.search(r'v(\d+\.\d+)', app['defaultSystemPrompt'][:500])
        if m: old_ver = m.group(1)

    new_ver = '?'
    m = re.search(r'v(\d+\.\d+)', latest_default[:500])
    if m: new_ver = m.group(1)

    if dry_run:
        print(f"  [DRY RUN] Would update defaultSystemPrompt: v{old_ver} -> v{new_ver}")
        results['defaultSystemPrompt'] = f"WOULD_UPDATE v{old_ver}->v{new_ver}"
    else:
        app['defaultSystemPrompt'] = latest_default
        print(f"  UPDATED: defaultSystemPrompt v{old_ver} -> v{new_ver}")
        results['defaultSystemPrompt'] = f"UPDATED v{old_ver}->v{new_ver}"

    # 2. Remove stale default_system_prompt (old format, adds bloat)
    if 'default_system_prompt' in app:
        stale_ver = '?'
        m = re.search(r'v(\d+\.\d+)', app['default_system_prompt'][:500])
        if m: stale_ver = m.group(1)
        if dry_run:
            print(f"  [DRY RUN] Would remove stale default_system_prompt v{stale_ver}")
        else:
            del app['default_system_prompt']
            print(f"  REMOVED: stale default_system_prompt v{stale_ver}")
        results['stale_removed'] = f"v{stale_ver}"
    else:
        print("  Already clean: no stale default_system_prompt")

    # 3. Sync promptTemplates with R2 canonical
    agent_names = {'PROJECTS-AGENT', 'PROMPTS-AGENT', 'QWAV-AGENT',
                   'EXPLORER-SUBAGENT', 'IMPLEMENTER-SUBAGENT', 'REVIEWER-SUBAGENT'}
    current_count = len(app.get('promptTemplates', []))
    # Merge: system prompts + templates
    all_prompts = all_entries  # Already includes both types

    if dry_run:
        print(f"  [DRY RUN] Would sync promptTemplates: {current_count} -> {len(all_prompts)} entries")
    else:
        app['promptTemplates'] = all_prompts
        print(f"  SYNCED: promptTemplates {current_count} -> {len(all_prompts)} entries")
    results['promptTemplates'] = f"{current_count}->{len(all_prompts)}"

    # 4. Save
    if not dry_run:
        backup_existing(ap_path)
        with open(ap_path, 'w', encoding='utf-8') as f:
            json.dump(app, f, indent=2, ensure_ascii=False)
        print(f"  SAVED: app-settings.json ({len(json.dumps(app)):,} bytes)")

    # Cleanup
    default_tmp.unlink(missing_ok=True)
    prompts_tmp.unlink(missing_ok=True)

    return results

# === RESTORE SKILLS ===
SKILL_MANIFEST = [
    "bling-usability-audit", "closeout-manager", "cloudflare-deployer",
    "email-composer", "git-hygiene", "kaizen-autonomous-update",
    "knowledge-graph", "local-to-r2-migration", "pdf-builder",
    "prompt-audit", "publication-publisher", "template-catalog",
]

def restore_skills(dry_run=False):
    """Restore skills from R2 to DeepChat skills directory."""
    print("\n" + "=" * 60)
    print("RESTORE: Skills")
    print("=" * 60)
    
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    
    for skill_name in SKILL_MANIFEST:
        local_tmp = Path(f"_tmp_skill_{skill_name}.md")
        r2_path = f"prompts/skills/{skill_name}/SKILL.md"
        
        if not r2_pull(r2_path, str(local_tmp), f"Pull {skill_name} skill"):
            print(f"  WARN: {skill_name} — SKILL.md not found on R2")
            results[skill_name] = "NOT ON R2"
            continue
        
        target_dir = SKILLS_DIR / skill_name
        target_file = target_dir / "SKILL.md"
        
        with open(local_tmp, encoding='utf-8') as f:
            content = f.read()
        
        if dry_run:
            print(f"  [DRY RUN] Would deploy {skill_name} ({len(content)} bytes)")
            results[skill_name] = "WOULD_DEPLOY"
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  DEPLOYED: {skill_name} ({len(content)} bytes)")
            results[skill_name] = "DEPLOYED"
        
        local_tmp.unlink(missing_ok=True)
    
    return results

# =====================================================================
# VERSION DRIFT CHECK (v2.2)
# =====================================================================

def check_drift(prompt_name='DEFAULT', prompt_path='prompts/DEFAULT.md', app_path=None):
    """Pull R2 canonical version, compare with local. Returns report dict."""
    import re
    if app_path is None:
        app_path = DEEPCHAT_DIR / 'app-settings.json'
    local_ver = None
    if Path(app_path).exists():
        with open(app_path, encoding='utf-8') as f:
            app = json.load(f)
        prompt = app.get('defaultSystemPrompt', '')
        m = re.search(r'v(\d+\.\d+)', prompt[:500])
        local_ver = m.group(1) if m else None
    r2_ver = None
    tmp = Path('_tmp_drift.md')
    ok, _ = run(
        f'npx wrangler r2 object get qnfo/{prompt_path} --remote --file={tmp}',
        f'Pull {prompt_name} version'
    )
    if ok and tmp.exists():
        with open(tmp, encoding='utf-8') as f:
            text = f.read()
        m = re.search(r'v(\d+\.\d+)', text[:500])
        r2_ver = m.group(1) if m else None
        tmp.unlink(missing_ok=True)
    report = {'prompt': prompt_name, 'local_version': local_ver, 'r2_version': r2_ver,
              'drift': local_ver != r2_ver if (local_ver and r2_ver) else None,
              'severity': 'ok', 'message': ''}
    if not local_ver:
        report.update(severity='error', message=f'{prompt_name}: cannot read local version')
    elif not r2_ver:
        report.update(severity='error', message=f'{prompt_name}: cannot read R2 version')
    elif local_ver != r2_ver:
        try:
            diff = abs(float(r2_ver) - float(local_ver))
        except ValueError:
            diff = 0
        if diff >= 1.0:
            report.update(severity='BLOCKING', drift=True,
                message=f'{prompt_name} v{local_ver} is {diff:.1f} versions behind R2 v{r2_ver}')
        elif diff >= 0.5:
            report.update(severity='warning', drift=True,
                message=f'{prompt_name} v{local_ver} behind R2 v{r2_ver}')
        else:
            report.update(severity='info', drift=True,
                message=f'{prompt_name} v{local_ver} slightly behind R2 v{r2_ver}')
    else:
        report['message'] = f'{prompt_name} v{local_ver} matches R2 canonical v{r2_ver}'
    return report

def check_all_drifts():
    """Check DEFAULT.md for version drift. Returns list of reports."""
    return [check_drift('DEFAULT', 'prompts/DEFAULT.md'), check_drift('QWAV', 'prompts/QWAV-DEFAULT.md')]

# === MAIN ===
def main():
    parser = argparse.ArgumentParser(
        description="DeepChat Quickstart — Full R2 Recovery (v2.3)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be restored")
    parser.add_argument("--prompts-only", action="store_true", help="Only restore prompts")
    parser.add_argument("--configs-only", action="store_true", help="Only restore configs")
    parser.add_argument("--skills-only", action="store_true", help="Only restore skills")
    parser.add_argument("--app-settings-only", action="store_true", help="Only update app-settings.json")
    parser.add_argument("--check-drift", action="store_true", help="Check version drift local vs R2 canonical")
    parser.add_argument("--backup-now", action="store_true", 
                       help="Backup current DeepChat settings to R2 (save state)")
    args = parser.parse_args()
    
    do_all = not (args.prompts_only or args.configs_only or args.skills_only or args.app_settings_only)
    
    print("=" * 60)
    print("DEEPCHAT QUICKSTART v2.3 — R2 Recovery")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'} {'BACKUP NOW' if args.backup_now else ''}")
    print(f"Canonical source: R2 bucket '{R2_BUCKET}'")
    print(f"Target (prompts/configs): {DEEPCHAT_DIR}")
    print(f"Target (skills): {SKILLS_DIR}")
    
    # --- Pre-flight check ---
    ok, out = run("npx wrangler whoami", "Cloudflare auth check")
    if not ok:
        print("\n" + "!" * 60)
        print("CLOUDFLARE AUTH FAILED!")
        print("!" * 60)
        print("Before running this script, set your Cloudflare API token:")
        print("  setx CLOUDFLARE_API_TOKEN \"your-40-char-token\"")
        print("Then restart your terminal and try again.")
        print("\nTo create a token: https://dash.cloudflare.com/profile/api-tokens")
        print("  → Create Token → Use template: 'Create Custom Token'")
        print("  → Permissions: Account → Cloudflare R2 Storage → Read")
        print("  → Account Resources: Include → quniverse")
        sys.exit(1)
    
    print(f"Cloudflare auth: OK ({out.strip()[:100]})")
    DEEPCHAT_DIR.mkdir(parents=True, exist_ok=True)
    
    # --- Backup current state ---
    if args.backup_now:
        print("\n" + "=" * 60)
        print("BACKUP: Saving current DeepChat state to R2")
        print("=" * 60)
        for fname, r2_path in CONFIG_MAP.items():
            src = DEEPCHAT_DIR / fname
            if src.exists():
                if r2_upload(str(src), r2_path):
                    print(f"  BACKED UP: {fname} -> {r2_path}")
                else:
                    print(f"  FAILED: {fname} (wrangler upload error)")
            else:
                print(f"  SKIP: {fname} (does not exist locally)")
    
    if args.check_drift:
        print("\n" + "=" * 60)
        print("VERSION DRIFT CHECK")
        print("=" * 60)
        results = check_all_drifts()
        for r in results:
            icon_map = {'ok': 'OK', 'info': 'INFO', 'warning': 'WARN', 'error': 'ERR', 'BLOCKING': 'BLOCK'}
            icon = icon_map.get(r['severity'], '?')
            print(f"  [{icon}] {r['message']}")
        blocking = any(r['severity'] == 'BLOCKING' for r in results)
        if blocking:
            print("\n  BLOCKING DRIFT! Run: python _quickstart_deepchat.py --app-settings-only")
        elif any(r['severity'] == 'warning' for r in results):
            print("\n  Drift detected. Run: python _quickstart_deepchat.py --app-settings-only")
        else:
            print("\n  All prompts current. No drift.")
        print("=" * 60)
        sys.exit(0 if not blocking else 1)
    
    # --- Restore ---
    if args.prompts_only or do_all:
        restore_prompts(dry_run=args.dry_run)
    
    if args.configs_only or do_all:
        restore_configs(dry_run=args.dry_run)
    
    if args.skills_only or do_all:
        restore_skills(dry_run=args.dry_run)
    
    if args.app_settings_only or do_all:
        restore_app_settings(dry_run=args.dry_run)
    
    # --- Done ---
    print("\n" + "=" * 60)
    print("RESTORE COMPLETE")
    print("=" * 60)
    if not args.dry_run:
        print("ACTION: Restart DeepChat for changes to take effect.")
        print()
        print("If this is a FRESH install, also configure:")
        print("  1. DeepChat → Settings → Providers → Add DeepSeek API key")
        print("  2. Restart DeepChat again after adding provider")


if __name__ == '__main__':
    main()
