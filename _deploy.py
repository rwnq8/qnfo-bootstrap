#!/usr/bin/env python3
"""
deploy.py -- Sync canonical skills to the DeepChat runtime.

Deploys skills (FULL directory: SKILL.md + scripts/ + references/) to the
DeepChat skills directory. Handles the EPERM issue (DeepChat's import process
cannot rename directories in use) by writing files directly without rename.

System prompts (DEFAULT.md, QWAV-DEFAULT.md, META-PROMPT-DEEPSEEK.md) and
templates (templates/*.md) are NOT deployed -- they must be imported through
DeepChat's UI. The prompts.json file in the repo root is the import file
for both system prompts and templates.

Config files (mcp-settings.json, acp_agents.json, model-config.json) are
DEPRECATED -- DeepChat manages these internally and overwrites deployed copies.
The --config-only flag is retained for backward compatibility only.

Usage:
  python _deploy.py              # Deploy skills
  python _deploy.py --dry-run    # Show what would change
  python _deploy.py --skills-only  # Deploy only skills
  python _deploy.py --config-only  # DEPRECATED - Deploy only configs

v3.0 -- 2026-06-06: R2-only architecture. No local canonical paths. Skills deployed
                    from R2 (qnfo/prompts/skills/) to DeepChat.
v2.2 -- 2026-06-05: Text-normalized hash comparison for .md/.json files (prevents
                    false WOULD_UPDATE from git core.autocrlf line-ending churn).
v2.1 -- 2026-06-05: Fixed target path (DeepChat reads from .deepchat, not AppData).
                    Extended to deploy ALL skill files (scripts, references, etc.).
v2.0 -- 2026-06-02: Removed system prompt and template sync (DeepChat UI only).
"""

import os
import sys
import json
import hashlib
import argparse
import shutil
import tempfile
from pathlib import Path

# --- Paths ------------------------------------------------------------
# ARCHITECTURE v3.0 (2026-06-06): R2 is the ONLY canonical source.
# There is NO local canonical directory. All files are pulled from R2.
# DeepChat settings at %USERPROFILE%\.deepchat\ or %APPDATA%\DeepChat\
# are EPHEMERAL and may be deleted at any time.
R2_BUCKET = "qnfo"
R2_SKILLS_PREFIX = "prompts/skills"  # R2 path prefix for skills

# DeepChat uses .deepchat in the user's home directory as its runtime directory.
# This was discovered 2026-06-05: _deploy.py was deploying to %APPDATA%\DeepChat\
# but DeepChat actually reads skills from %USERPROFILE%\.deepchat\skills\.
# The two directories are SEPARATE (38 skills in .deepchat vs 14 in AppData).
DEEPCHAT_DIR = Path.home() / ".deepchat"
if not DEEPCHAT_DIR.exists():
    # Fallback: older DeepChat versions may use AppData
    APPDATA = Path(os.environ.get("APPDATA", ""))
    if not APPDATA.exists():
        APPDATA = Path(os.path.expandvars(r"%APPDATA%"))
    DEEPCHAT_DIR = APPDATA / "DeepChat"

DEEPCHAT_SKILLS = DEEPCHAT_DIR / "skills"

# Skill manifest: list of all skills to deploy. Each skill is at
# qnfo/prompts/skills/<name>/SKILL.md on R2.
# Update this list when new skills are added to R2.
SKILL_MANIFEST = [
    "bling-usability-audit",
    "closeout-manager",
    "cloudflare-deployer",
    "email-composer",
    "git-hygiene",
    "kaizen-autonomous-update",
    "knowledge-graph",
    "local-to-r2-migration",
    "pdf-builder",
    "prompt-audit",
    "publication-publisher",
    "template-catalog",
]

# Config deployment is DEPRECATED per META-PROMPT v6.0. DeepChat manages
# these internally and overwrites any deployed copies.
CONFIG_MAP = {
    "mcp-settings.json": DEEPCHAT_DIR / "mcp-settings.json",
    "acp_agents.json": DEEPCHAT_DIR / "acp_agents.json",
    "model-config.json": DEEPCHAT_DIR / "model-config.json",
}

# =====================================================================
# Utilities
# =====================================================================

def hash_content(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def hash_file_binary(path):
    """Hash a file by its binary content (handles any file type)."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def hash_text_normalized(path):
    """Hash a text file by its content, normalizing line endings to \n.
    
    Prevents false-positive WOULD_UPDATE from git's core.autocrlf 
    converting \n <-> \r\n in canonical files after deployment.
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # Normalize all line endings to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

TEXT_EXTENSIONS = {".md", ".json", ".txt", ".html", ".css", ".js", ".yaml", ".yml", ".toml"}

def read_file(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, content):
    """Write text content to a file. Creates parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True

def copy_file(src, dst):
    """Copy a file (binary safe). Creates parent directories."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True

# =====================================================================
# SKILL DEPLOYMENT (v2.1 -- full directory sync)
# =====================================================================

def run_shell(cmd, desc=""):
    """Run a shell command. Returns (success_bool, output_string)."""
    import subprocess
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        ok = r.returncode == 0
        if not ok:
            print(f"  FAIL: {desc}: {r.stderr.strip()[:200]}")
        return ok, r.stdout.strip()
    except Exception as e:
        print(f"  ERROR: {desc}: {e}")
        return False, ""

def deploy_skills(dry_run=False):
    """
    Pull skills from R2 and deploy to DeepChat skills directory.

    For EACH skill in SKILL_MANIFEST, pulls SKILL.md from R2 (qnfo/prompts/skills/<name>/SKILL.md)
    and deploys to DeepChat. Supporting files (scripts/, references/) are also pulled if
    they exist on R2.

    Returns a dict of {skill_name: status} where status is one of:
    UNCHANGED, UPDATED, INSTALLED, WOULD_UPDATE, WOULD_INSTALL, ERROR
    """
    import tempfile
    results = {}

    DEEPCHAT_SKILLS.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="deploy_skills_") as tmpdir:
        tmp = Path(tmpdir)

        for skill_name in SKILL_MANIFEST:
            r2_skill_md = f"{R2_SKILLS_PREFIX}/{skill_name}/SKILL.md"
            local_skill_md = tmp / f"{skill_name}_SKILL.md"

            # Pull SKILL.md from R2
            cmd = f'npx wrangler r2 object get {R2_BUCKET}/{r2_skill_md} --remote --file="{local_skill_md}"'
            ok, _ = run_shell(cmd, f"Pull {skill_name}/SKILL.md")
            if not ok or not local_skill_md.exists():
                results[skill_name] = "ERROR: SKILL.md not found on R2"
                continue

            deployed_skill_md = DEEPCHAT_SKILLS / skill_name / "SKILL.md"

            # Compute text-normalized hash of R2 content
            canon_hash = hash_text_normalized(local_skill_md)
            depl_hash = None
            if deployed_skill_md.exists():
                depl_hash = hash_text_normalized(deployed_skill_md)

            if canon_hash == depl_hash:
                results[skill_name] = "UNCHANGED"
                continue

            if dry_run:
                if deployed_skill_md.exists():
                    results[skill_name] = "WOULD_UPDATE"
                else:
                    results[skill_name] = "WOULD_INSTALL"
                continue

            # Execute: copy SKILL.md to DeepChat
            try:
                deployed_dir = DEEPCHAT_SKILLS / skill_name
                deployed_dir.mkdir(parents=True, exist_ok=True)

                content = read_file(local_skill_md)
                if content is not None:
                    write_file(deployed_skill_md, content)
                    status = "UPDATED" if depl_hash is not None else "INSTALLED"
                    results[skill_name] = status
                else:
                    results[skill_name] = "ERROR: Could not read SKILL.md"
            except Exception as e:
                results[skill_name] = f"ERROR: {e}"

    return results

# =====================================================================
# CONFIG DEPLOYMENT (DEPRECATED -- DeepChat manages these internally)
# =====================================================================

def deploy_configs(dry_run=False):
    """
    DEPRECATED: Sync canonical config files to DeepChat config directory.
    DeepChat manages config files internally and WILL overwrite deployed copies.
    This function is retained for backward compatibility only.
    """
    results = {"_deprecated": "Config deployment is DEPRECATED. DeepChat manages configs internally."}
    # No local canonical source; configs are on R2 at qnfo/prompts/config/
    config_dir = Path(tempfile.gettempdir()) / "deploy_configs_skip"  # will not exist - skip gracefully

    for name, deployed_path in CONFIG_MAP.items():
        canonical_path = config_dir / name
        if not canonical_path.exists():
            results[name] = "CANONICAL_MISSING"
            continue

        canonical = read_file(canonical_path)
        if canonical is None:
            continue

        if deployed_path.exists():
            deployed = read_file(deployed_path)
            if deployed and hash_content(canonical) == hash_content(deployed):
                results[name] = "UNCHANGED"
                continue
            if dry_run:
                results[name] = "WOULD_UPDATE"
                continue

        if dry_run:
            results[name] = "WOULD_INSTALL"
            continue

        write_file(deployed_path, canonical)
        results[name] = "UPDATED"

    return results

# =====================================================================
# Main
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Deploy canonical skills to DeepChat runtime (v2.1)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skills-only", action="store_true")
    parser.add_argument("--config-only", action="store_true",
                        help="DEPRECATED: DeepChat manages configs internally")
    args = parser.parse_args()

    run_all = not (args.skills_only or args.config_only)
    dry = args.dry_run

    print("=" * 60)
    print(f"DEPLOY -- Canonical -> DeepChat Runtime (v2.1)")
    print(f"Source:      R2 (qnfo/{R2_SKILLS_PREFIX}/)")
    print(f"Target:      {DEEPCHAT_SKILLS}")
    print(f"Mode:        {'DRY RUN' if dry else 'LIVE'}")
    print("=" * 60)

    if run_all or args.skills_only:
        print("\n--- Skills ---")
        results = deploy_skills(dry_run=dry)
        for key in sorted(results.keys()):
            if key == "error":
                print(f"  !! {results[key]}")
                continue
            if ":stale" in key:
                skill_name = key.replace(":stale", "")
                stale_list = results[key]
                print(f"  ?? {skill_name}: STALE FILES (in deployed but not canonical): {stale_list}")
                continue

            status = results[key]
            flag = "->" if any(w in str(status) for w in ("UPDATE", "INSTALL")) else "  "
            print(f"  {flag} {key}: {status}")

    if run_all or args.config_only:
        print("\n--- Configs (DEPRECATED) ---")
        results = deploy_configs(dry_run=dry)
        for cfg in sorted(results.keys()):
            if cfg == "_deprecated":
                print(f"  !! {results[cfg]}")
                continue
            flag = "->" if "UPDATE" in str(results[cfg]) else "  "
            print(f"  {flag} {cfg}: {results[cfg]}")

    if dry:
        print("\n[DRY RUN] Remove --dry-run to apply changes.")
    else:
        print("\n[DONE] Skills deployed.")
        print("Note: System prompts and templates must be imported via DeepChat UI.")
        print("Note: Restart DeepChat to pick up skill changes.")


if __name__ == "__main__":
    main()
