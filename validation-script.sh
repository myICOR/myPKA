#!/usr/bin/env bash
# validation-script.sh — verify a folder is myPKA scaffold v2.x-compliant.
#
# Usage:
#   bash validation-script.sh <scaffold-root>
#
# Exit codes:
#   0  = compliant
#   1  = one or more checks failed (see stderr)
#   2  = invalid invocation
#
# Dependencies: bash, find, grep, awk, head, wc, basename, dirname. Standard Unix.

set -u

if [ $# -ne 1 ]; then
  echo "Usage: $0 <scaffold-root>" >&2
  exit 2
fi

ROOT="$1"

if [ ! -d "$ROOT" ]; then
  echo "FAIL: '$ROOT' is not a directory" >&2
  exit 2
fi

FAILS=0
WARNS=0

fail() {
  echo "FAIL: $1" >&2
  FAILS=$((FAILS + 1))
}

warn() {
  echo "WARN: $1" >&2
  WARNS=$((WARNS + 1))
}

pass() {
  echo "ok:   $1"
}

# ----------------------------------------------------------------------------
# 1. .scaffold-version exists and is in the v2.x, v3.x, or v4.x line
# ----------------------------------------------------------------------------
# All v2.x releases (2.0.x, 2.1.x, ...) share the same structural requirements,
# so any 2.x value passes this check. v2.0.0 is the six-specialist base;
# v2.1.0 added adapter-generated host-native slash commands (no structural
# change). v3.x and v4.x were the bundled-download line (Cockpit + agent packs
# preinstalled), structural supersets of v2.x, so they pass the same checks;
# v4.0.0 additionally ADDED the self-update framework files (manifest.json,
# scripts/update-scaffold.py + check-version.py, the update-scaffold slash
# command). v5.0.0 unbundles the two agent packs (back to the six core
# specialists; the Cockpit stays bundled); every required dir, SOP, and
# guideline this script enforces is still present, so it passes the same
# checks. Bump the regex to a tighter line only when a release introduces
# structural changes that this script must enforce.

VERSION_FILE="$ROOT/.scaffold-version"
if [ ! -f "$VERSION_FILE" ]; then
  fail ".scaffold-version not found at $VERSION_FILE"
else
  VERSION=$(head -n1 "$VERSION_FILE" | tr -d '[:space:]')
  case "$VERSION" in
    2.*)
      pass ".scaffold-version is $VERSION (v2.x line)"
      ;;
    3.*)
      pass ".scaffold-version is $VERSION (v3.x bundled line)"
      ;;
    4.*)
      pass ".scaffold-version is $VERSION (v4.x self-updating line)"
      ;;
    5.*)
      pass ".scaffold-version is $VERSION (v5.x basic-plus-cockpit line)"
      ;;
    *)
      fail ".scaffold-version is '$VERSION', expected '2.x', '3.x', '4.x', or '5.x'"
      ;;
  esac
fi

# ----------------------------------------------------------------------------
# 2. Task folders exist
# ----------------------------------------------------------------------------

for sub in open in-progress done cancelled; do
  DIR="$ROOT/Team Knowledge/tasks/$sub"
  if [ -d "$DIR" ]; then
    pass "tasks/$sub/ exists"
  else
    fail "tasks/$sub/ missing at $DIR"
  fi
done

# Catch the common mistake of creating a blocked/ folder. Blocked tasks live in in-progress/ with blocked_reason set.
if [ -d "$ROOT/Team Knowledge/tasks/blocked" ]; then
  warn "tasks/blocked/ exists but should not — blocked tasks live in in-progress/ with blocked_reason set in frontmatter"
fi

# ----------------------------------------------------------------------------
# 3. Required task templates and INDEX
# ----------------------------------------------------------------------------

for f in "_template.md" "INDEX.md"; do
  PATH_F="$ROOT/Team Knowledge/tasks/$f"
  if [ -f "$PATH_F" ]; then
    pass "tasks/$f exists"
  else
    fail "tasks/$f missing at $PATH_F"
  fi
done

# ----------------------------------------------------------------------------
# 4. Per-agent journal folders + templates
# ----------------------------------------------------------------------------

if [ ! -d "$ROOT/Team" ]; then
  fail "Team/ directory missing at $ROOT/Team"
else
  AGENTS_FOUND=0
  while IFS= read -r AGENTS_FILE; do
    AGENT_DIR=$(dirname "$AGENTS_FILE")
    AGENT_NAME=$(basename "$AGENT_DIR")
    AGENTS_FOUND=$((AGENTS_FOUND + 1))

    JOURNAL_DIR="$AGENT_DIR/journal"
    if [ ! -d "$JOURNAL_DIR" ]; then
      fail "no journal/ for agent '$AGENT_NAME' (expected at $JOURNAL_DIR)"
    else
      pass "journal/ exists for '$AGENT_NAME'"
      if [ ! -f "$JOURNAL_DIR/_template.md" ]; then
        warn "no _template.md in '$AGENT_NAME' journal/"
      fi
    fi
  done < <(find "$ROOT/Team" -mindepth 2 -maxdepth 2 -name "AGENTS.md" -type f 2>/dev/null)

  if [ "$AGENTS_FOUND" -eq 0 ]; then
    warn "no agent AGENTS.md files found under Team/ — folder may be empty or non-standard"
  else
    pass "scanned $AGENTS_FOUND agent(s) for journal compliance"
  fi
fi

# ----------------------------------------------------------------------------
# 5. Required SOPs exist
# ----------------------------------------------------------------------------

REQUIRED_SOPS=(
  "SOP-create-task.md"
  "SOP-claim-task.md"
  "SOP-close-task.md"
  "SOP-list-open-tasks.md"
  "SOP-rebuild-task-index.md"
  "SOP-write-journal-entry.md"
  "SOP-read-own-journal.md"
  "SOP-write-session-log.md"
)

for sop in "${REQUIRED_SOPS[@]}"; do
  if [ -f "$ROOT/Team Knowledge/SOPs/$sop" ]; then
    pass "SOP exists: $sop"
  else
    fail "SOP missing: Team Knowledge/SOPs/$sop"
  fi
done

# ----------------------------------------------------------------------------
# 6. No tsk-*.md files outside the tasks/ tree (catch accidental spillage)
# ----------------------------------------------------------------------------

STRAY=$(find "$ROOT" -name "tsk-*.md" -type f 2>/dev/null | grep -v "/Team Knowledge/tasks/" || true)
if [ -n "$STRAY" ]; then
  fail "stray tsk-*.md files outside tasks/ tree:"
  echo "$STRAY" | sed 's/^/      /' >&2
else
  pass "no stray tsk-*.md files"
fi

# ----------------------------------------------------------------------------
# 7. No path-based wikilinks to tasks/ (must be basename-only)
# ----------------------------------------------------------------------------

# Look for [[tasks/... or [[Team Knowledge/tasks/... patterns in any markdown file under root.
# Backtick-quoted matches are documentation citing the forbidden pattern (e.g. the
# CHANGELOG-MIGRATION.md checklist line that quotes `[[tasks/<status>/...]]` to teach
# the rule) — filter those out so the check does not match its own documentation.
PATHLINKS=$(grep -rE '\[\[(Team Knowledge/)?tasks/' "$ROOT" --include='*.md' 2>/dev/null \
  | grep -vE '`[^`]*\[\[(Team Knowledge/)?tasks/[^`]*`' || true)
if [ -n "$PATHLINKS" ]; then
  warn "path-based wikilinks to tasks/ found (should be basename-only — see SOP-rebuild-task-index):"
  echo "$PATHLINKS" | head -10 | sed 's/^/      /' >&2
  if [ "$(echo "$PATHLINKS" | wc -l)" -gt 10 ]; then
    echo "      ...(truncated)" >&2
  fi
else
  pass "no path-based task wikilinks"
fi

# ----------------------------------------------------------------------------
# 8. Frontmatter sanity: each task file has id+title+assignee+priority+status
# ----------------------------------------------------------------------------

TASK_FILES=$(find "$ROOT/Team Knowledge/tasks" -name "tsk-*.md" -type f 2>/dev/null || true)
TASKS_CHECKED=0
TASKS_BAD=0

if [ -n "$TASK_FILES" ]; then
  while IFS= read -r tf; do
    TASKS_CHECKED=$((TASKS_CHECKED + 1))
    MISSING=""
    for field in "id" "title" "assignee" "priority" "status" "created" "updated" "created_by" \
                 "linked_sops" "linked_workstreams" "linked_guidelines" \
                 "linked_my_life" "linked_session_logs" "linked_journal_entries"; do
      if ! awk -v fld="$field" '
        BEGIN { in_fm=0 }
        NR==1 && /^---$/ { in_fm=1; next }
        in_fm && /^---$/ { exit 1 }
        in_fm && $0 ~ "^"fld":" { found=1; exit 0 }
        END { exit (found ? 0 : 1) }
      ' "$tf" 2>/dev/null; then
        MISSING="$MISSING $field"
      fi
    done
    if [ -n "$MISSING" ]; then
      fail "task '$tf' missing required frontmatter:$MISSING"
      TASKS_BAD=$((TASKS_BAD + 1))
    fi

    # status field must match folder
    FOLDER=$(basename "$(dirname "$tf")")
    case "$FOLDER" in
      open|in-progress) EXPECTED="$FOLDER" ;;
      [0-9][0-9]) # month folder under done/ or cancelled/
        PARENT_OF_PARENT=$(basename "$(dirname "$(dirname "$tf")")")
        case "$PARENT_OF_PARENT" in
          done|cancelled) EXPECTED="$PARENT_OF_PARENT" ;;
          *) EXPECTED="" ;;
        esac
        ;;
      *) EXPECTED="" ;;
    esac
    if [ -n "$EXPECTED" ]; then
      ACTUAL=$(awk '
        BEGIN { in_fm=0 }
        NR==1 && /^---$/ { in_fm=1; next }
        in_fm && /^---$/ { exit }
        in_fm && /^status:/ { sub(/^status:[ ]*/, ""); print; exit }
      ' "$tf")
      if [ "$ACTUAL" != "$EXPECTED" ]; then
        warn "task '$tf' has status '$ACTUAL' but folder is '$EXPECTED'"
      fi
    fi
  done <<< "$TASK_FILES"
  pass "checked $TASKS_CHECKED task file(s); $TASKS_BAD with frontmatter issues"
else
  pass "no task files yet (clean v1.10.x install)"
fi

# ----------------------------------------------------------------------------
# 9. Agnosticism audit (v4 tool-agnostic core)
# ----------------------------------------------------------------------------
# Scans the PORTABLE CORE only — PKM/, Team Knowledge/, and the body of every
# Team/*/AGENTS.md — and explicitly EXCLUDES .claude/ (host-specific shims are
# allowed to name Claude Code constructs; the portable contract must not).
#
# HARD FAIL when the portable core contains a host-coupling token:
#   - the literal ".claude/"
#   - "subagent_type" (Claude-Code dispatch key)
#   - a hardcoded model id baked into prose
#   - (co-owned with Vex) ~/.claude/.credentials.json / OAuth-token reuse /
#     a client-fingerprint header
#   - a slash-command cited as the ONLY trigger with no natural-language trigger
# WARN when:
#   - a contract leans on Claude-specific reasoning behavior as load-bearing
#   - an MCP server name appears with no "harness-config" caveat nearby

echo
echo "--- agnosticism-audit (v4 tool-agnostic core) ---"

# Build the list of files that make up the portable core.
# PKM/ and Team Knowledge/ in full; from Team/ only the per-agent AGENTS.md files.
#
# SCOPE (v5.1.0): the audit checks portable-core DOCTRINE, not operational
# record and not third-party pack content. Excluded from the scan:
#   - Team Knowledge/session-logs/** — user-generated operational record. A
#     session log that truthfully names a host path (e.g. documenting shim
#     work per WS-003) must not fail the member's validator.
#   - Expansions/** — Expansion content is governed by the pack author and the
#     WS-003 security gate, not by this audit.
#   - Team/<folder>/AGENTS.md for agents installed BY an Expansion — same
#     ruling: pack-shipped contract bytes must not be able to fail or warn the
#     member's scaffold validator. Installed-pack agent folders are read from
#     Expansions/_installed/*/.manifest.json and Expansions/*/expansion.yaml.
CORE_FILES=""
for d in "PKM" "Team Knowledge"; do
  if [ -d "$ROOT/$d" ]; then
    while IFS= read -r f; do
      CORE_FILES="$CORE_FILES
$f"
    done < <(find "$ROOT/$d" -type f -name '*.md' -not -path '*/session-logs/*' 2>/dev/null)
  fi
done
if [ -d "$ROOT/Team" ]; then
  while IFS= read -r f; do
    CORE_FILES="$CORE_FILES
$f"
  done < <(find "$ROOT/Team" -mindepth 2 -maxdepth 2 -name "AGENTS.md" -type f 2>/dev/null)
fi
# Strip the leading blank line and any path under a .claude/ or Expansions/
# segment (belt and braces).
CORE_FILES=$(printf '%s\n' "$CORE_FILES" | grep -v '^$' | grep -v '/\.claude/' | grep -v '/Expansions/' || true)

# Drop pack-installed agent contracts: collect `folder:` values from installed
# Expansion manifests (JSON snapshot or live expansion.yaml) and exclude each
# Team/<folder>/AGENTS.md from the scan.
PACK_AGENT_EXCLUDED=0
PACK_FOLDERS=$( { cat "$ROOT"/Expansions/_installed/*/.manifest.json "$ROOT"/Expansions/*/expansion.yaml 2>/dev/null || true; } \
  | grep -oE '"?folder"?[[:space:]]*:[[:space:]]*"[^"]+"' \
  | sed -E 's/.*:[[:space:]]*"([^"]+)"/\1/' | sort -u)
if [ -n "$PACK_FOLDERS" ]; then
  while IFS= read -r pf; do
    [ -n "$pf" ] || continue
    if printf '%s\n' "$CORE_FILES" | grep -qF "/Team/$pf/AGENTS.md"; then
      CORE_FILES=$(printf '%s\n' "$CORE_FILES" | grep -vF "/Team/$pf/AGENTS.md" || true)
      PACK_AGENT_EXCLUDED=$((PACK_AGENT_EXCLUDED + 1))
    fi
  done <<< "$PACK_FOLDERS"
fi
if [ "$PACK_AGENT_EXCLUDED" -gt 0 ]; then
  pass "agnosticism scope: excluded $PACK_AGENT_EXCLUDED pack-installed agent contract(s) (governed by the pack author, not this audit)"
fi

# Meta-documentation allowlist: files whose SUBJECT is the host-coupling boundary
# itself, so they MUST cite the forbidden tokens to teach the rule. These are the
# only files exempt wholesale. Everything else is scanned. Matched by basename.
#   GL-005 — defines the portable-core boundary; names .claude/ as the adapter dir.
#   GL-002 — the contract-frontmatter `model:` section documents the alias, the
#            example provider/model-id, and the ~/.claude/.credentials.json ToS rule.
#   SOP-001 — the hiring flow authors the per-harness shim under .claude/agents/.
META_ALLOWLIST_RE='(GL-005-llm-agnostic-portable-core|GL-002-frontmatter-conventions|SOP-001-how-to-add-a-new-specialist)\.md$'

# Per-line escape hatch: a line carrying the marker  agnosticism-audit:allow
# is a deliberate, reviewed citation (e.g. a contract quoting a token to explain
# why it is forbidden). The marker keeps the exemption auditable and grep-able.
ALLOW_MARKER='agnosticism-audit:allow'

# core_grep <extended-regex> — grep the portable core, print "file:line:match".
# Returns matches on stdout (empty if none). Skips .claude/, the meta allowlist,
# and any individual line carrying the allow marker.
core_grep() {
  local pattern="$1"
  [ -z "$CORE_FILES" ] && return 0
  printf '%s\n' "$CORE_FILES" | while IFS= read -r f; do
    [ -n "$f" ] || continue
    printf '%s' "$f" | grep -qE "$META_ALLOWLIST_RE" && continue
    grep -nE "$pattern" "$f" 2>/dev/null \
      | grep -vF "$ALLOW_MARKER" \
      | sed "s|^|$f:|"
  done
}

report_hits() {
  # report_hits <hits> <indent-label>
  printf '%s\n' "$1" | head -10 | sed 's/^/      /' >&2
  if [ "$(printf '%s\n' "$1" | wc -l)" -gt 10 ]; then
    echo "      ...(truncated)" >&2
  fi
}

AGNO_BEFORE=$FAILS

# --- HARD FAIL: literal ".claude/" reference in the portable core ---
HITS=$(core_grep '\.claude/' || true)
if [ -n "$HITS" ]; then
  fail "portable core references '.claude/' (host-coupling; keep host paths in shims only):"
  report_hits "$HITS"
else
  pass "no '.claude/' references in portable core"
fi

# --- HARD FAIL: subagent_type (Claude-Code dispatch key) ---
HITS=$(core_grep 'subagent_type' || true)
if [ -n "$HITS" ]; then
  fail "portable core references 'subagent_type' (Claude-Code-specific dispatch key):"
  report_hits "$HITS"
else
  pass "no 'subagent_type' references in portable core"
fi

# --- HARD FAIL: hardcoded model id baked into prose ---
# Provider-pinned model slugs (claude-*, gpt-*, gemini-*, us.anthropic.*, anthropic/claude-*).
# The portable contract should use the alias form (reasoning|balanced|fast) per GL-002.
HITS=$(core_grep '(claude-[0-9a-z]|gpt-[0-9]|gemini-[0-9]|us\.anthropic\.|anthropic/claude-|opus-[0-9]|sonnet-[0-9]|haiku-[0-9])' || true)
if [ -n "$HITS" ]; then
  fail "portable core contains a hardcoded model id (use the model: alias reasoning|balanced|fast per GL-002):"
  report_hits "$HITS"
else
  pass "no hardcoded model ids in portable core"
fi

# --- HARD FAIL (co-owned with Vex): credential / OAuth-token reuse ---
HITS=$(core_grep '(\.claude/\.credentials\.json|credentials\.json|OAuth[ -]?token reuse|subscription[ -]?(OAuth|token)|x-app|client-fingerprint|anthropic-?client)' || true)
if [ -n "$HITS" ]; then
  fail "portable core references credential/OAuth-token reuse or a client-fingerprint header (Vex co-owned, ToS INVARIANT):"
  report_hits "$HITS"
else
  pass "no credential/OAuth-token-reuse references in portable core"
fi

# --- HARD FAIL: slash-command cited as the ONLY trigger ---
# A line that mentions a /slash-command but contains no natural-language trigger
# alongside it. We flag lines naming a slash command that ALSO assert it is the
# sole path ("only", "must use", "run /x to"). Conservative: only flags when a
# slash command appears with an exclusivity word and no "or"/"also"/"trigger".
HITS=$(core_grep '/(close-session|larry|process-inbox|clarify|delegate)[^a-z]' \
  | grep -iE '(only|must (run|use)|sole|exclusively)' \
  | grep -ivE '(natural[ -]language|trigger|also|or say|phrase)' || true)
if [ -n "$HITS" ]; then
  fail "portable core cites a slash-command as the ONLY trigger (pair it with a natural-language trigger):"
  report_hits "$HITS"
else
  pass "no slash-command-only triggers in portable core"
fi

# --- WARN: Claude-specific reasoning behavior as load-bearing ---
HITS=$(core_grep '(extended thinking|interleaved thinking|thinking budget|Claude-specific|Anthropic-specific) (is |as )?(required|load-bearing|needed|relied)' || true)
if [ -n "$HITS" ]; then
  warn "portable core may assume Claude-specific reasoning behavior as load-bearing:"
  report_hits "$HITS"
else
  pass "no load-bearing Claude-specific reasoning assumptions detected"
fi

# --- WARN: a specific MCP server NAME without a "harness-config" caveat ---
# Targets a *named* MCP server (e.g. "supabase MCP server", "FooMCP",
# "mcp__<name>__"), not the bare acronym in generic prose about installing MCP.
# A named server is a harness-config detail; it should carry a caveat that it is
# only available when the host has wired it.
HITS=$(core_grep '(mcp__[a-z0-9_]+|[A-Za-z0-9-]+ MCP server|[A-Za-z0-9]+MCP)' \
  | grep -ivE 'harness[- ]config|host[- ]config|if (available|configured|wired|present)|when (available|configured|wired)|optional|caveat|where (available|configured)|any [A-Za-z -]*MCP|a new MCP|an MCP server|install MCP|install a MCP|install an MCP|if any|deregister MCP|set up MCP|MCP server registrations|[0-9]+(\.[0-9]+)* MCP servers' || true)
if [ -n "$HITS" ]; then
  warn "named MCP server reference(s) in portable core without a 'harness-config' caveat:"
  report_hits "$HITS"
else
  pass "named MCP references (if any) carry a harness-config caveat"
fi

if [ "$FAILS" -eq "$AGNO_BEFORE" ]; then
  pass "agnosticism-audit: portable core is host-agnostic"
fi

# ----------------------------------------------------------------------------
# 10. SSOT consistency: manifest.json present and scaffold_version == VERSION
# ----------------------------------------------------------------------------
# Light, transitional gate. WARN (never hard-fail) while v4 is still being
# assembled — manifest.json may not have landed yet.

MANIFEST="$ROOT/manifest.json"
VERSION_SSOT_FILE="$ROOT/VERSION"
if [ ! -f "$MANIFEST" ]; then
  warn "manifest.json not found at $MANIFEST (transitional build — expected once v4 lands)"
else
  MANIFEST_VER=$(grep -oE '"scaffold_version"[[:space:]]*:[[:space:]]*"[^"]*"' "$MANIFEST" \
    | head -n1 | sed -E 's/.*"scaffold_version"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/')
  if [ -z "$MANIFEST_VER" ]; then
    warn "manifest.json has no parseable scaffold_version field"
  elif [ ! -f "$VERSION_SSOT_FILE" ]; then
    warn "VERSION file not found at $VERSION_SSOT_FILE — cannot cross-check manifest scaffold_version ($MANIFEST_VER)"
  else
    VERSION_VALUE=$(head -n1 "$VERSION_SSOT_FILE" | tr -d '[:space:]')
    if [ "$MANIFEST_VER" = "$VERSION_VALUE" ]; then
      pass "manifest.json scaffold_version ($MANIFEST_VER) matches VERSION ($VERSION_VALUE)"
    else
      warn "manifest.json scaffold_version ($MANIFEST_VER) != VERSION ($VERSION_VALUE) — SSOT drift"
    fi
  fi
fi

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------

echo
echo "========================================"
echo "Validation summary for $ROOT"
echo "  Failures: $FAILS"
echo "  Warnings: $WARNS"
echo "========================================"

if [ "$FAILS" -gt 0 ]; then
  exit 1
fi

exit 0
