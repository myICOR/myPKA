# Images - Index

Single shared image bucket for your entire myPKA. Journal entries, CRM People entries, and Documents all embed images from here.

## Structure

`PKM/Images/YYYY/MM/YYYY-MM-DD-<slug>.<ext>`

Auto-create rule: when Penn or another agent saves a new image and the `YYYY/` or `MM/` subfolder does not exist, the agent creates it.

## SSOT for images

An image lives in exactly one location: `PKM/Images/YYYY/MM/`. Anywhere it shows up (Journal, CRM, Documents) it is referenced via `![[Images/YYYY/MM/...]]`, never duplicated into another folder.

## Filename pattern

`YYYY-MM-DD-<slug>.<ext>`

Examples:
- `2026-05-04-business-card-dr-schmidt.png`
- `2026-05-04-whiteboard-q3-roadmap.jpg`

The slug describes what is in the image. Avoid generic slugs like `screenshot` or `photo` unless that is genuinely all the context you have. See [[GL-001-file-naming-conventions]].

## Active files

- `2026/05/2026-05-04-dr-schmidt-business-card.png` — seeded course sample, embedded from [[dr-schmidt]].
- `2026/05/2026-05-04-sample-screenshot.png` — seeded course sample, embedded from [[2026-05-04-first-day]].

Penn saves further images here as you share them.

## Subfolders by year

- `2026/` (current year, with `05/` pre-created)

New years and months are created on demand by whoever is writing the new image.
