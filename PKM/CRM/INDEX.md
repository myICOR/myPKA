# CRM - Index

People and Organizations the user interacts with. Cross-linked into Journal entries via `[[wikilinks]]`.

## Subsections

- **People/** - one file per person. Filename: kebab-case of the name (`dr-schmidt.md`).
- **Organizations/** - one file per organization (`dr-schmidt-clinic.md`).

## Active files

- People: [[dr-schmidt]] — seeded course sample.
- Organizations: [[dr-schmidt-clinic]] — seeded course sample.

These two files plus the seeded Journal entry are the SSOT demo the course walks through — four files, one input, no duplication. Penn adds further entries here as people and organizations show up in the Journal.

## How the CRM stays in sync

- Penn creates a stub in `People/` or `Organizations/` whenever a new name shows up in Journal input.
- The stub is the source of truth for that person or organization. Journal entries link to it via `[[wikilinks]]`.
- Updates to a person's role, contact info, or notes go in the CRM file, not the Journal entry.

## Naming

- Person: kebab-case of how the user refers to them. `dr-schmidt`, `maria-garcia`, `tom-roedl`.
- Organization: kebab-case, with enough words to disambiguate. `dr-schmidt-clinic` rather than `clinic`.
- See [[GL-001-file-naming-conventions]] for collision rules.

## Cross-links

- Person → Organization they belong to.
- Organization → People at the org.
- Both → the Journal entries that mention them.
- Both → relevant Topics in [[PKM/My Life/INDEX|My Life]].
