# Documents - Index

Markdown stubs that describe and point at the user's real documents (passports, contracts, IDs, certificates). The actual files often live elsewhere (cloud drive, encrypted vault). The stub holds metadata, expiration dates, and links.

## Active files

- [[passport]] — seeded course sample. Shows the canonical shape of a document stub.

## What goes here

- Identity documents (passport, ID card, driver's license).
- Contracts the user wants to remember exists, even if the binary file lives in a vault.
- Certificates (degrees, training, certifications).
- Any official document that needs metadata captured in markdown.

## What does not go here

- Daily notes (those go in [[PKM/Journal/INDEX|Journal]]).
- Personal projects or goals (those go in [[PKM/My Life/INDEX|My Life]]).
- Research reports (those go in `Deliverables/`).

## Naming

Kebab-case slug. No date prefix. One file per document.

Examples: `passport.md`, `passport-renewal-2032.md`, `rental-contract-berlin-flat.md`.

See [[GL-001-file-naming-conventions]].

## Image embeds

If a document has scans, those go to `PKM/Images/YYYY/MM/` and are embedded via `![[Images/YYYY/MM/...]]` from the document stub. The image is in Images. The stub points at it. SSOT.
