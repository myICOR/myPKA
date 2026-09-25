---
type: agent-bio
agent: Silas
role: Structure and database architect
created: 2026-09-04
---

# Silas

![[silas.png|240]]

Silas keeps your vault in shape. Every note carries the fields the
scaffold expects, every live table (a Base) shows the notes it claims
to show, and real databases sit in the Databases room instead of
scattered copies of your notes. When you bring in an old vault or an
export from another tool, Silas makes sure it lands in the right
shape, not just the right folder.

## What Silas does for you

- Audits your notes: missing fields, wrong names, broken links, and a
  fix per finding
- Runs the vault health check at session start, on request and after
  every import; repairs to your notes go to Penn, with your yes
- Adds a new frontmatter field the right way (guideline first, then
  template, then your existing notes)
- Decides when a collection earns a live table and creates it
- Keeps the Databases room honest: sources in, mirrors out
- Maps an import from another tool onto this vault's structure and
  checks the result before you accept it

## When to call Silas

"Audit my notes", "are my Projects consistent", "I need a new field on
People", "should this be a Base", "check what the import produced".

## Silas works with

- [[GL-1001-the-six-rooms]]
- [[GL-1002-frontmatter-conventions]]
- [[GL-1004-naming-rules]]
- [[GL-1006-bases-and-live-views]]
- [[GL-1005-code-vs-instructions]]
- [[WS-1004-import-and-convert-external-knowledge]]
- [[SOP-1010-convert-an-external-note]]
- [[SOP-1011-import-or-align-an-external-agent]]
- [[SOP-1012-convert-an-external-skill]]

## Under the hood

Silas's system prompt lives in [[06 AI Team/Agents/Silas/AGENT|AGENT.md]].
