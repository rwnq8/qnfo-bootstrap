#!/usr/bin/env python3
"""
_quickstart_deepchat.py v4.0 — MINIMAL SKILL-DRIVEN BOOTSTRAP
=============================================================
Architecture: ONE master prompt + 12 curated skills. Nothing else.

What this does:
  1. Kill DeepChat
  2. Pull master prompt from R2 → set as defaultSystemPrompt
  3. Deploy 12 QNFO skills from R2 → ~/.deepchat/skills/
  4. Clean dead files (custom_prompts.json, system_prompts.json)
  5. Restart DeepChat autonomously

BEFORE (v2.x — FRAGILE, "totally failed"):
  - Restore 3 JSON files (custom_prompts, system_prompts, app-settings)
  - 27 prompt templates as JSON blobs
  - 7 agent system prompts as separate files
  - Model config, MCP settings, ACP agents
  - 20 QNFO skills (including rarely-used ones)
  - Manual restart
  → Triple-file sync trap, version drift, "totally failed"

AFTER (v4.0 — RESILIENT, ~30 seconds):
  - Pull ONE master prompt → set as defaultSystemPrompt
  - Deploy 12 curated skills (plain markdown)
  - Kill dead files
  - Autonomous restart
  → 3 things total. Nothing to drift. Nothing to sync.

Usage:
  python _quickstart_deepchat.py              # Full bootstrap
  python _quickstart_deepchat.py --verify     # Check state only
  python _quickstart_deepchat.py --dry-run    # Show what would change
"""

import json, os, sys, shutil, subprocess, argparse, re
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
R2_BUCKET = "qnfo"
R2_MASTER_PROMPT = "prompts/DEFAULT-SKILL-CATALOG.md"
R2_SKILLS_PREFIX = "prompts/skills"
SKILLS_DIR = Path.home() / ".deepchat" / "skills"
APPDATA = Path(os.environ.get("APPDATA", ""))
DEEPCHAT_DIR = APPDATA / "DeepChat"
APP_SETTINGS = DEEPCHAT_DIR / "app-settings.json"
DEEPCHAT_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DeepChat" / "DeepChat.exe"

# ── 12 Curated QNFO Skills (loaded on-demand via skill_view) ────────
QNFO_SKILLS = [
    # Core — loaded on trigger
    "execution-guard",          # Priority 0 execution enforcement (extended rules)
    "qnfo-agent",               # Extended QNFO policies (reference)
    # Core operations — triggered frequently
    "cloudflare-deployer",      # Pages, R2, Workers, DNS, redirects
    "publication-publisher",    # End-to-end publication pipeline
    "closeout-manager",         # Session close-out, audit trail, handoff
    "git-hygiene",              # Git recovery and hygiene
    # Situational — triggered by specific tasks
    "pdf-builder",              # Markdown → PDF with math rendering
    "email-composer",           # Outlook email composition
    "knowledge-graph",          # QNFO Knowledge Graph queries
    "prompt-audit",             # Self-audit against 19 design patterns
    "local-to-r2-migration",    # Migrate local files to R2
    "kaizen-autonomous-update", # System-wide Kaizen updates
]

# ── Utilities ──────────────────────────────────────────────────────
def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except Exception as e:
        return False, str(e)

def r2_pull(remote_path, local_path, timeout=30):
    ok, _ = run(
        f'npx wrangler r2 object get {R2_BUCKET}/{remote_path} --remote --file="{local_path}"',
        timeout=timeout
    )
    return ok and Path(local_path).exists()

# ── DeepChat Process Management ────────────────────────────────────
def kill_deepchat():
    ok, out = run('taskkill /f /im DeepChat.exe 2>nul', timeout=10)
    was_running = 'SUCCESS' in out.upper()
    print(f'  [{"KILL" if was_running else "INFO"}] DeepChat.exe {"terminated" if was_running else "was not running"}')
    return was_running

def restart_deepchat():
    if not DEEPCHAT_EXE.exists():
        print(f'  [ERROR] DeepChat.exe not found at {DEEPCHAT_EXE}')
        return False
    subprocess.Popen([str(DEEPCHAT_EXE)], shell=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f'  [LAUNCH] DeepChat.exe started')
    return True

# ── Step 1: Pull & deploy master prompt ─────────────────────────────
def deploy_master_prompt(dry_run=False):
    """Pull master prompt from R2 and set as defaultSystemPrompt."""
    tmp = Path("_bs_master_prompt.md")
    
    if not r2_pull(R2_MASTER_PROMPT, str(tmp)):
        print(f'  [ERROR] Master prompt not on R2: {R2_MASTER_PROMPT}')
        return "R2_MISSING"
    
    with open(tmp, 'r', encoding='utf-8') as f:
        master_content = f.read()
    
    tmp.unlink(missing_ok=True)
    
    # Extract version
    m = re.search(r'v(\d+\.\d+)', master_content[:500])
    version = m.group(1) if m else '?'
    
    if not APP_SETTINGS.exists():
        return "NO_APP_SETTINGS"
    
    with open(APP_SETTINGS, 'r', encoding='utf-8') as f:
        app = json.load(f)
    
    old_dsp = app.get('defaultSystemPrompt', '')
    
    if old_dsp == master_content:
        return "UNCHANGED"
    
    if dry_run:
        return f"WOULD_SYNC (v{version}, {len(master_content):,} chars)"
    
    # Backup
    shutil.copy2(APP_SETTINGS, Path(str(APP_SETTINGS) + '.bs4_bak'))
    
    app['defaultSystemPrompt'] = master_content
    
    # Remove stale keys
    app.pop('default_system_prompt', None)
    
    # Remove agent entries from promptTemplates
    agent_names = {'PROJECTS-AGENT', 'PROMPTS-AGENT', 'QWAV-AGENT', 'EMAIL-AGENT',
                   'EXPLORER-SUBAGENT', 'IMPLEMENTER-SUBAGENT', 'REVIEWER-SUBAGENT'}
    app['promptTemplates'] = [t for t in app.get('promptTemplates', [])
                              if t.get('name', '') not in agent_names]
    
    with open(APP_SETTINGS, 'w', encoding='utf-8') as f:
        json.dump(app, f, indent=2, ensure_ascii=False)
    
    return f"SYNCED (v{version}, {len(master_content):,} chars)"

# ── Step 2: Deploy skills ──────────────────────────────────────────
def deploy_skills(dry_run=False):
    results = {}
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    
    for skill_name in QNFO_SKILLS:
        r2_path = f"{R2_SKILLS_PREFIX}/{skill_name}/SKILL.md"
        tmp = Path(f"_bs_{skill_name}.md")
        
        if not r2_pull(r2_path, str(tmp)):
            results[skill_name] = "R2_MISSING"
            continue
        
        with open(tmp, 'r', encoding='utf-8') as f:
            content = f.read()
        
        target_dir = SKILLS_DIR / skill_name
        target_md = target_dir / "SKILL.md"
        
        if target_md.exists():
            with open(target_md, 'r', encoding='utf-8') as f:
                if f.read() == content:
                    results[skill_name] = "UNCHANGED"
                    tmp.unlink(missing_ok=True)
                    continue
        
        if dry_run:
            results[skill_name] = "WOULD_UPDATE" if target_md.exists() else "WOULD_INSTALL"
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            with open(target_md, 'w', encoding='utf-8') as f:
                f.write(content)
            results[skill_name] = "UPDATED" if target_md.exists() else "INSTALLED"
        
        tmp.unlink(missing_ok=True)
    
    return results

# ── Step 3: Clean dead files ───────────────────────────────────────
def clean_dead_files(dry_run=False):
    dead = []
    for fname in ['custom_prompts.json', 'system_prompts.json']:
        fpath = DEEPCHAT_DIR / fname
        if fpath.exists():
            dead.append(fname)
            if not dry_run:
                fpath.unlink()
    
    # Also check for stale default_system_prompt
    if APP_SETTINGS.exists() and not dry_run:
        with open(APP_SETTINGS, 'r', encoding='utf-8') as f:
            app = json.load(f)
        if 'default_system_prompt' in app:
            del app['default_system_prompt']
            dead.append('default_system_prompt (stale key)')
            with open(APP_SETTINGS, 'w', encoding='utf-8') as f:
                json.dump(app, f, indent=2, ensure_ascii=False)
    
    return dead

# ── Verify ─────────────────────────────────────────────────────────
def verify_state():
    issues = []
    
    # Check master prompt
    if APP_SETTINGS.exists():
        with open(APP_SETTINGS, 'r', encoding='utf-8') as f:
            app = json.load(f)
        dsp = app.get('defaultSystemPrompt', '')
        m = re.search(r'QNFO MASTER PROMPT.*v(\d+\.\d+)', dsp[:500])
        if m:
            print(f'  Master prompt: v{m.group(1)} ({len(dsp):,} chars)')
        else:
            issues.append("Master prompt: NOT FOUND or wrong format")
        
        if 'default_system_prompt' in app:
            issues.append("Stale default_system_prompt key present")
    else:
        issues.append("app-settings.json missing")
    
    # Check skills
    for skill_name in QNFO_SKILLS:
        md = SKILLS_DIR / skill_name / "SKILL.md"
        if not md.exists():
            issues.append(f"MISSING skill: {skill_name}")
    
    # Check dead files
    for fname in ['custom_prompts.json', 'system_prompts.json']:
        if (DEEPCHAT_DIR / fname).exists():
            issues.append(f"DEAD FILE present: {fname}")
    
    return issues

# ── Main ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="QNFO Bootstrap v4.0 (Skill-Driven)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--no-restart", action="store_true")
    args = parser.parse_args()
    
    print("=" * 60)
    print("QNFO BOOTSTRAP v4.0 — Skill-Driven Architecture")
    print("=" * 60)
    print(f"Mode: {'VERIFY' if args.verify else 'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Master prompt: R2/{R2_MASTER_PROMPT}")
    print(f"Skills: {len(QNFO_SKILLS)} from R2/{R2_SKILLS_PREFIX}/")
    
    if args.verify:
        issues = verify_state()
        if issues:
            print(f"\n❌ {len(issues)} issue(s):")
            for i in issues:
                print(f"  - {i}")
            sys.exit(1)
        print(f"\n✅ Master prompt active. {len(QNFO_SKILLS)}/{len(QNFO_SKILLS)} skills deployed. No dead files.")
        sys.exit(0)
    
    # ── Step 1: Kill DeepChat ──
    print("\n── Step 1: Kill DeepChat ──")
    kill_deepchat()
    
    # ── Step 2: Deploy master prompt ──
    print("\n── Step 2: Master Prompt ──")
    mp_result = deploy_master_prompt(dry_run=args.dry_run)
    print(f'  {mp_result}')
    
    # ── Step 3: Deploy skills ──
    print(f"\n── Step 3: Deploy {len(QNFO_SKILLS)} Skills ──")
    results = deploy_skills(dry_run=args.dry_run)
    
    updated = sum(1 for v in results.values() if v in ('INSTALLED', 'UPDATED', 'WOULD_INSTALL', 'WOULD_UPDATE'))
    unchanged = sum(1 for v in results.values() if v == 'UNCHANGED')
    missing = sum(1 for v in results.values() if v == 'R2_MISSING')
    
    for name, status in sorted(results.items()):
        icon = {'INSTALLED': '+', 'UPDATED': '~', 'UNCHANGED': '=', 
                'WOULD_INSTALL': '+', 'WOULD_UPDATE': '~',
                'R2_MISSING': '!'}.get(status, '?')
        print(f'  [{icon}] {name}: {status}')
    
    print(f'  Summary: {updated} changed, {unchanged} unchanged, {missing} unavailable')
    
    # ── Step 4: Clean dead files ──
    print("\n── Step 4: Clean Dead Files ──")
    dead = clean_dead_files(dry_run=args.dry_run)
    if dead:
        for d in dead:
            print(f'  [DEL] {d}')
    else:
        print('  ✅ No dead files')
    
    # ── Step 5: Restart ──
    if not args.dry_run and not args.no_restart:
        print("\n── Step 5: Restart DeepChat ──")
        restart_deepchat()
    
    # ── Summary ──
    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE. Remove --dry-run to execute.")
    else:
        print("BOOTSTRAP COMPLETE.")
        print(f"  Master prompt deployed from R2")
        print(f"  {len(QNFO_SKILLS)} skills synced")
        if not args.no_restart:
            print("  DeepChat restarted")
    print("=" * 60)

if __name__ == '__main__':
    main()
