# Contributing

Thanks for being interested in myPKA. A short note on how this repo handles contributions.

## What this repo is

myPKA is the working slice of the **ICOR methodology** as practiced by Paperless Movement S.L. The scaffold's structure, agent contracts, and operating rules reflect deliberate methodology choices. Changes flow top-down from the maintainers, not bottom-up from PRs.

## Pull Requests

**This repo does not accept pull requests.** PRs that arrive will be closed with a friendly note pointing here.

If you want to improve your own version of the scaffold, **fork it freely**. The license (CC BY-SA 4.0) explicitly allows you to adapt, remix, and build on the material with attribution and share-alike. That's the right path for personal customizations and experiments.

## Licensing of contributions

If you send us anything that lands in the scaffold, whether through an issue, an
accepted WS-002 tool pattern, or any other route, you license it to Paperless
Movement S.L. under the same terms as the file it lands in (CC BY-SA 4.0 for the
base scaffold), and you confirm it is yours to give. This keeps the scaffold's
licensing clean and lets us relicense it in future without having to track down
every contributor. If that does not work for you, say so in the issue and we will
leave your suggestion out.

## Issues

Issues are accepted for a narrow set of cases:

- Typo fixes and broken links in the docs
- Clearly reproducible bugs in `SOP-002-convert-mypka-to-sqlite.md` (the migration prompt)
- Reproducible bugs in `Team Knowledge/scripts/migrate-inline-fields-to-frontmatter.py` (the v1.3.0 inline-fields migration helper)
- Factual errors in scaffold content (a wrong USPTO number, an outdated URL, etc.)

Use the issue templates so the right one gets routed quickly.

## Note shape and frontmatter

Every entity note (Person, Organization, Project, Goal, Habit, Topic, Key Element, Document) is shaped by `Team Knowledge/Guidelines/GL-002-frontmatter-conventions.md` and starts from a template in `Team Knowledge/Templates/`. Field names match SQLite column names in `SOP-002-convert-mypka-to-sqlite.md`. If you fork and want to add or rename a field, edit GL-002 first, then update the matching template — the SOP and the Templates inherit field names from the Guideline by `[[wikilink]]`, not by copy.

## Adding new tool patterns to WS-002

`Team Knowledge/Workstreams/WS-002-import-external-knowledge-base.md` ships with a starter set of source-tool signatures (Heptabase, Notion, Obsidian, Roam, Logseq, Mem, Capacities, Apple Notes, Evernote, Tana via MCP, etc.). If you run an import and discover a new export format quirk — a fresh signature for sniffing, an undocumented tag-encoding convention, a SQLite schema variant — that's a community contribution candidate. Open an issue with: source tool name + version, the smallest folder/file fingerprint that identifies it, and the mapping that worked for you. Approved patterns land in WS-002 directly.

## Methodology questions, "how do I adapt this for X", anything deeper

The right home for those conversations is the **myICOR community**, where the team and other members can engage on your specific case.

Join at **[https://myicor.com](https://myicor.com)**.

This isn't a redirect to upsell - it's a redirect to the venue where these conversations actually go somewhere. Public forums on a methodology repo dilute the canon and split community attention. The membership keeps the depth where the depth lives.

## Discussions

Disabled on this repo for the same reason. Use the [myICOR community](https://myicor.com) for community Q&A.

## Forks

Encouraged. The license permits adaptation for any purpose, including commercial, with attribution and share-alike. If you build something useful on top of myPKA, share it through the myICOR community - we'll feature good work.
