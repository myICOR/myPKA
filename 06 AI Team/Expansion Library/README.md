# Expansion Library

Optional add-ons that ship with myPKA but are **not switched on**. Nothing in
this folder runs or installs by itself, and your AI does not look at it at
session start.

## Install one

1. Copy the zip into `06 AI Team/Expansions/` and unzip it there, so the
   result is `06 AI Team/Expansions/<pack-id>/`.
2. Tell your AI: "I added an expansion to `06 AI Team/Expansions`. Inspect it,
   explain what it adds and install it through the expansion workflow."
   It follows WS-1006 and asks before it copies anything.

## What is here

| Pack | What it does | Note |
| --- | --- | --- |
| `converter-pack-v1.1.2.zip` (Voice & File Converter) | Turns voice memos, recordings and video links into searchable text, and converts everyday file formats (images and PDF, Word and Markdown, audio, web pages), all on your own computer. | Written for the older folder layout (myPKA 5). Its `ADAPT-EXPANSION.md` tells your AI how to map it onto this folder; let it show you the plan before it installs. It downloads a speech model (Whisper) when you first use it. |
| `handwritten-collaboration-loop-v1.0.2.zip` (Handwritten Collaboration Loop) | Brings handwritten notes and sketches from any handwriting app into the folder, and sends finished work back as PDFs you can annotate by hand. | Written for the older folder layout (it files into `PKM/raw-footage/`, and expects a `deliverable-formats` guideline this folder does not have). Your AI must adapt it with you; its `ADAPT-EXPANSION.md` is the starting point. |

## Already part of your team

These packs from the Tool Lab are not here because what they added is now in
the team itself:

- **Vex, Felix, Vera, Pixel** (the four agent packs) are team members since
  myPKA 7.0.0.
- **App Developer Pack** (Felix, Vex, Vera) and **Designer Pack** (Iris,
  Charta, Pixel): every agent they added is in the team, in a newer version.
  Do not install them over this folder; they would add older copies of the
  same agents.

## Licence

Both packs are MIT as part of myPKA 7, like the rest of this folder (see
`LICENSE` and `LICENSE-MAP.md`). The "proprietary" licence line inside each
zip is from when they were sold separately; the licensor has added the MIT
licence for every copy, so you may use, change and share them on MIT terms.

An experiment, not a product: you are responsible for what you install and
run, and for its security. When in doubt, ask Vex to review a pack before it
runs.
