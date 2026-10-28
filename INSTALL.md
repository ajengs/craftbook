# Installing craftbook skills

Each skill is a folder with a `SKILL.md` and its own supporting files, under `skills/<name>/`. The format is the Agent Skills layout that several agents read. Where your agent looks for skills differs by tool, so this guide gives the common ones. Paths were checked against public docs and guides on 2026-10-28. Tools change, so confirm against your agent's own documentation if something doesn't load.

Start by cloning the repo:

```bash
git clone https://github.com/ajengs/craftbook.git
cd craftbook
```

**Link or copy.** Linking keeps the repo as the source of truth: a `git pull` updates every agent that points at it. Copying is simpler, but you re-copy after each update. A skill needs its whole folder, not just `SKILL.md`.

## Claude Code

Claude Code reads skills from `~/.claude/skills/<name>` (all projects) or `<repo>/.claude/skills/<name>` (one project). The folder must sit directly in that directory.

One skill, linked (Linux and macOS, then Windows):

```bash
mkdir -p ~/.claude/skills
ln -sfn "$PWD/skills/artifex" ~/.claude/skills/artifex
```

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
New-Item -ItemType Junction -Path "$HOME\.claude\skills\artifex" -Target "$PWD\skills\artifex"
```

Every skill, linked. Linux and macOS:

```bash
mkdir -p ~/.claude/skills
for s in skills/*/; do ln -sfn "$PWD/${s%/}" ~/.claude/skills/"$(basename "$s")"; done
```

Every skill, linked. Windows (PowerShell), with directory junctions, which need no admin rights:

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Get-ChildItem skills -Directory | ForEach-Object { New-Item -ItemType Junction -Path "$HOME\.claude\skills\$($_.Name)" -Target $_.FullName }
```

To copy instead, use `cp -r skills/<name> ~/.claude/skills/` or `Copy-Item skills\<name> "$HOME\.claude\skills\" -Recurse`. Start a new session so the skills are picked up.

## Claude.ai (chat, Cowork, cloud)

Account skills are uploaded one zip at a time, so build one zip per skill:

```bash
mkdir -p dist
(cd skills && zip -r ../dist/artifex.zip artifex)
```

```powershell
New-Item -ItemType Directory -Force dist | Out-Null
Compress-Archive -Path skills\artifex -DestinationPath dist\artifex.zip
```

Then upload it in your account's skill settings, under Settings, then Capabilities, then Skills, or under Customize, then Skills, depending on your version. Skills need code execution enabled and a plan that includes Skills.

Sources disagree on the zip layout. If the upload rejects a zip that contains the `artifex/` folder, zip the folder's contents instead, so `SKILL.md` sits at the top of the archive.

## Codex CLI

Codex reads skills from `~/.codex/skills/<name>` (user) or `.codex/skills/<name>` (project). Some guides also mention `~/.agents/skills`. Restart Codex after adding skills.

```bash
mkdir -p ~/.codex/skills
for s in skills/*/; do ln -sfn "$PWD/${s%/}" ~/.codex/skills/"$(basename "$s")"; done
```

## Gemini CLI

Gemini CLI has a skills command that can link a repo's skills into your user folder (`~/.gemini/skills`, or `~/.agents/skills`):

```bash
gemini skills link "$PWD/skills"
```

To install one skill from the Git repo instead, use `gemini skills install <repo-url> --path skills/artifex`. Then run `/skills reload` and check `/skills list`. If a command fails, run `gemini skills --help`, since the command shapes may differ by version.

## Other agents

Cursor, GitHub Copilot, Pi and many others have adopted the same `SKILL.md` format, but their directories differ and published sources conflict (for example `.cursor/skills/`, `.github/skills/`, `.agents/skills/`). Check your agent's documentation for its skills directory, and link or copy the skill folders there. `~/.agents/skills/` is a shared convention that some agents read. Pi's directory is `~/.pi/agent/skills/`; run `/reload` there.

If your agent has no skills feature, use a skill as plain instructions: tell the agent to read `skills/<name>/SKILL.md` and follow it, and to read the files it references only when a step needs them.

## What may not carry over

Some behavior depends on the environment, not on the files:
- sub agents and session creation (Artifex's umbrella, P3 to P6)
- commentable document artifacts
- schedulers (the optional status page, polling fallback)

Artifex falls back where it can: its Optional tools table names a fallback for each tool, and it writes markdown files when no document system exists. Skills that mention another skill by name need that skill installed, or they use the written fallback.

## Check it worked

Start a new session and ask the agent which skills it has, or invoke one directly, for example `/artifex` in Claude Code.
