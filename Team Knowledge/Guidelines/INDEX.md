# Guidelines - Index

**Guidelines are general rules every agent reads on every relevant action.** Where SOPs are skills (procedures the agent runs) and Workstreams are compositions (multi-agent choreography), Guidelines are the static rules and constraints that hold the whole system together. Naming, frontmatter, design system. SOPs and Workstreams `[[wikilink]]` to Guidelines rather than duplicating the rules.

Filename pattern: `GL-NNN-<title>.md`.

## Active Guidelines

| GL | Title | Description |
|---|---|---|
| GL-001 | [[GL-001-file-naming-conventions]] | Kebab-case rules, ISO date prefix on date-driven files, slug rules, image filename pattern. |
| GL-002 | [[GL-002-frontmatter-conventions]] | YAML frontmatter field schemas for all 8 entity types, typing rules, foreign-key convention. Aligns with [[SOP-002-convert-mypka-to-sqlite]]. |
| GL-004 | [[GL-004-task-resource-linking]] | One-way Task → Resource linking rule, seven-array task frontmatter contract, `linked_deliverables` slug format, archive-on-close cascade. Read by [[SOP-create-task]], [[SOP-claim-task]], [[SOP-close-task]]. |
| GL-005 | [[GL-005-llm-agnostic-portable-core]] | The portable-core boundary: harness-agnostic core (`PKM/`, `Team Knowledge/`, the body of every `Team/*/AGENTS.md`) vs the per-harness adapter layer (`.claude/`, future `.codex/`, `.cursor/`). No harness names, host tool names, slash-command-only triggers, or hardcoded models in the core. Enforced by the `agnosticism-audit` in `validation-script.sh`. <!-- agnosticism-audit:allow --> |

*Reserved:* GL-003, the design-system Guideline (the visual identity SSOT). It ships with the Designer Pack, available with the myICOR membership on the Expansion Packs page; installing the pack adds `GL-003-design-system.md` to this set. Next free Guideline slot for locally-authored rules is GL-006.

## When to write a new Guideline

- The rule is static and applies across many files or procedures.
- More than one SOP or Workstream needs to know about it.
- Without it, you would copy-paste the same rule into multiple files.

If you find yourself restating the same rule in two files, stop and write a Guideline. Then `[[wikilink]]` to it from both files.
