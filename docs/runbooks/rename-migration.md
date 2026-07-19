# Runbook — migrating a clone after the terrella rename

The repo moved to `terrella-project/terrella` under its new name
([ADR-0008](../adr/ADR-0008-project-name-terrella.md)). GitHub redirects the old URL, so
stale clones keep working — but update each machine when convenient. Machines with clones:
earth (both WSL distros and/or Fedora), jupiter, Mac mini.

## Per-machine checklist

1. **Point the remote at the new home** (works even if you skip the directory move):

   ```bash
   cd ~/src/earth-ai   # or wherever the clone lives
   git remote set-url origin git@github.com:terrella-project/terrella.git
   git fetch origin && git pull
   ```

2. **Before moving the directory**, check nothing points at the old path:

   ```bash
   crontab -l | grep -i earth-ai
   systemctl --user list-unit-files | grep -i earth
   ```

   The repo's own scripts hardcode no absolute paths, but machine-local automation might.

3. **Move the directory** (optional but keeps docs accurate):

   ```bash
   mv ~/src/earth-ai ~/src/terrella
   ```

4. **Claude Code memory gotcha:** project auto-memory is keyed by the directory path.
   After moving, copy the old memory over so it isn't orphaned:

   ```bash
   cp -r ~/.claude/projects/-home-<user>-src-earth-ai/memory \
         ~/.claude/projects/-home-<user>-src-terrella/
   ```

   (Directory names are the absolute path with `/` → `-`; create the target if the new
   path hasn't been opened in Claude Code yet.)

5. **Continue.dev users:** regenerate the assistant config — the sync script now writes
   `terrella-config.yaml` (was `earth-ai-config.yaml`); remove the old file from
   `~/.continue/assistants/` if present.

## What NOT to touch

The `Earth-AI` WSL distro, the `earth-ai` Tailscale hostname, and the
`name: earth-ai` compose project are live infrastructure and keep their names until M0
retires them (see [ADR-0008](../adr/ADR-0008-project-name-terrella.md) and the naming
rules in [AGENTS.md](../../AGENTS.md)).
