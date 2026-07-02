# Runbook: GitHub Project setup

How to stand up and maintain the declarative project-management sync. See
[docs/project-management.md](../project-management.md) for the model itself.

## Prerequisites

- Maintainer access to the `mkzsystems` org.
- The [`gh`](https://cli.github.com/) CLI, authenticated with a session that has
  `admin:org` and `project` scopes (`gh auth refresh -s admin:org,project`).

## What the sync manages

[`scripts/project-sync.sh`](../../scripts/project-sync.sh) reconciles, **non-destructively**,
from [`.github/project.yml`](../../.github/project.yml):

- repo **labels** (create/update/rename via `from:`),
- phase **milestones** M0–M7 (create/update),
- org **issue types** (validate-only),
- the org **Project board** custom fields (validate-only).

It never deletes anything absent from the spec. Preview with:

```bash
bash scripts/project-sync.sh --dry-run
```

## One-time board creation

Custom fields are scriptable; views and auto-add are UI-only:

```bash
OWNER=mkzsystems
gh project create --owner "$OWNER" --title "earth-ai 1.0"
# Note the returned project number, set it as `project.number` in .github/project.yml, then:
NUM=<number>
gh project field-create "$NUM" --owner "$OWNER" --name "Effort" \
  --data-type SINGLE_SELECT --single-select-options "XS,S,M,L,XL"
gh project field-create "$NUM" --owner "$OWNER" --name "Order"       --data-type NUMBER
gh project field-create "$NUM" --owner "$OWNER" --name "Start Date"  --data-type DATE
gh project field-create "$NUM" --owner "$OWNER" --name "Target Date" --data-type DATE
```

## Running the sync locally

```bash
bash scripts/project-sync.sh
```

Verify:

```bash
gh label list -R mkzsystems/earth-ai --limit 100
gh api repos/mkzsystems/earth-ai/milestones --jq '.[].title'
gh project field-list <NUM> --owner mkzsystems
```

## Running it in CI (unattended)

The [`project-sync`](../../.github/workflows/project-sync.yml) workflow runs on pushes to
`main` that touch the spec, and on manual dispatch. It needs a maintainer PAT because org
issue types and org Projects cannot be written by the default `GITHUB_TOKEN`.

1. Create a PAT with `repo`, `project`, and org read (`admin:org`) scopes — or reuse the
   org's existing `PROJECT_ADMIN_TOKEN` used by astrocyte.
2. Add it as the repo secret **`PROJECT_ADMIN_TOKEN`**
   (`gh secret set PROJECT_ADMIN_TOKEN -R mkzsystems/earth-ai`).
3. Trigger a run: `gh workflow run project-sync.yml` (or push a spec change).

Until the secret exists, the workflow still runs but exits `0` with a warning and makes no
changes.

## Auto-add automation (UI-only)

New issues and pull requests are added to the board by the Project's **built-in workflows**
(Project ⚙ → Workflows), not a repo Action:

- **Auto-add to project** — adds new items from `mkzsystems/earth-ai` to the board.
- **Auto-add sub-issues to project** — pulls in sub-issues of tracked issues.

Enable both when creating the board; confirm after any board rebuild.

## Board views (UI-only)

The API cannot create or configure views. Create these three:

| View | Layout | Config | Purpose |
|---|---|---|---|
| **Roadmap** | Roadmap | Group by `Milestone`; dates from Start/Target Date | Timeline across M0–M7 |
| **Board** | Board | Columns by `Status` (`Todo / In Progress / Done`) | Day-to-day kanban |
| **Open Items** | Table | Filter `is:issue -status:Done` | Triage and bulk editing |

Tip (from astrocyte): to browse by subsystem, add a table view **sliced by Labels** — an
issue can carry several `component:*` labels, and the slice sidebar filters one at a time.
After editing any view, use the view's ▾ menu → **Save changes**, or it reverts on reload.
