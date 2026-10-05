---
type: sop
id: SOP-2041
title: Generate a styled image
created: 2026-09-26
owner: pixel
uses: ["[[SOP-1013-connect-an-external-tool-via-mcp]]", "[[SOP-1006-start-work-and-archive-a-wip-folder]]", "[[GL-1004-naming-rules]]", "[[GL-1005-code-vs-instructions]]"]
skill_name: pixel-styled-image
skill_summary: "Make a still image in the user's own style from a brief and references, with three variants and a receipt, or write an image brief when no generator is connected."
skill_triggers:
  - "make me a thumbnail"
  - "create a hero image"
  - "design a quote card"
  - "stylize this image"
  - "use these references and generate"
---

# SOP-2041 Generate a styled image

Pixel's procedure from a brief to a finished still image in the user's
style. Any agent that needs a styled visual can follow it. Shipped by
the Pixel expansion pack; the pack number range is explained in the
pack's README.

Runs when the user says "make me a thumbnail", "create a hero image",
"design a quote card", "stylize this", "use these references and
generate X", "make this look photographic / illustrated / painted",
or "the image generator is not available, can we still do this".

Inputs: the brief (what the image is of, what it is for, where it will
be seen), the format, any reference images, any words that go on the
image (verbatim from the user), and optionally a Charta layout to
finish.

1. [JUDGEMENT] **Read the style.** Open the user's design-system
   guideline, only the sections this image needs: palette, imagery
   direction, type roles for text on the image, voice for any caption.
   A needed section is empty: route to Iris first (preferred), or, for
   a small job the user wants now, work in a neutral style (editorial
   photo, neutral palette, system type) and note "neutral style,
   design-system section missing" in the deliverable.
2. [JUDGEMENT] **Pick the path.**
   - A: a generator is available (built into the model, a connected
     image MCP, or a configured API). Use the one the user named as
     their default; if it is down after one retry and the image is due,
     another path is an exception, and the receipt names it and why.
     When the job carries a real person's reference, the switch waits
     for the user's go: those photos would go to a service the user did
     not choose for them.
     Go to step 3.
   - B: none is available and the user wants one. Name the options
     (an image-capable MCP server from the vendor, the vendor's image
     API) and hand the connection to Mack through
     [[SOP-1013-connect-an-external-tool-via-mcp|SOP-1013]]. Return to
     step 3 once it answers.
   - C: the user does not want a generator. Go to step 9.
   Never fall to C without offering B.
3. [JUDGEMENT] **Write the prompt in five parts, in this order.**
   1. Format: "Generate a 16:9 landscape image." Pin it here and again
      in the requirements at the end; models default to square.
   2. Identity anchor, only when a real person is in the frame: "Using
      the attached reference photo of <name>, ..." first, before the
      scene. No supplied photo, no person.
   3. Scene: concrete nouns and actions ("a person at a walnut desk
      writing in an open notebook"), no adjectives yet.
   4. Material and light: textures, one light source, time of day,
      palette words taken from the design system.
   5. Style and negatives: the imagery direction, then every exclusion
      said outright ("no text, no logos, no busy background").
   Rewrite on sight: adjective soup, contradictions ("minimal but rich
   in detail"), "like the previous one" with nothing attached, a person
   described instead of referenced.
4. [JUDGEMENT] **Attach references through the model's reference
   input**, never described in prose. Identity references first, taken
   only from the user's reference folder for that person. Three to five
   references for most jobs, each adding a distinct cue (identity,
   palette, composition, material, mood). Write down the file path of
   each one; the receipt carries them.
5. [JUDGEMENT] **Set every parameter.** On every call set the aspect
   ratio, quality, resolution or size, and any style preset or variant
   the service offers, explicitly. Do not rely on a default; check the
   service's own help for which settings it has. Note the values; they
   go into the receipt.
6. [JUDGEMENT] **Generate three variants with a hypothesis each.**
   - A, safe: closest to the brand and the literal brief.
   - B, evolved: A with one strong move (composition, light, focal
     point).
   - C, bold: a genuinely different idea, possibly outside the brief.
   Write each hypothesis down before generating. One variant only when
   the user asked for one. Raw output goes to a working subfolder, not
   to the final location.
7. [JUDGEMENT] **Score each image, and check every face.**

   | Factor | Question |
   | --- | --- |
   | Composition | Does the eye land on the focal point at once? |
   | Clarity | Can the subject be said in one sentence? |
   | Brand fit | Do palette, light and material match the design system? |
   | Contrast | Does it hold up on the background it will be seen on? |
   | Specificity | Is there one concrete detail that makes it not generic? |
   | Type | Is any text readable, and spelled right, at the size it will be seen, on a phone? |
   | Faithfulness | Does it deliver the prompt and the user's request? |
   | Identity | Does every real person's face match their reference, side by side? |

   Fails three or more: rewrite the prompt. Fails one or two: change
   only what failed (light, crop, palette). A frame whose face does not
   match the reference is discarded, never shipped, and the report says
   which service and model drew it.
8. [JUDGEMENT] **Show before delivering.** Put the variants side by
   side with their hypotheses and scores, say which is ready and which
   needs a pass, and wait for the user's pick. Iterate from step 3 as
   asked. Go to step 10.
9. [JUDGEMENT] **Path C, the brief.** Write `design-brief.md` in the
   work folder: subject and purpose, the five-part prompt ready to
   paste, the reference list, format, size and quality to set, style
   notes from the design system, and three prompt variations to try if
   the first misses. The brief is the deliverable; the user renders it.
10. [JUDGEMENT] **Deliver with the receipt.** The approved image goes
    to `YYYY-MM-DD-<topic-slug>/` in the WiP folder that asked
    ([[SOP-1006-start-work-and-archive-a-wip-folder|SOP-1006]]), named
    per [[GL-1004-naming-rules|GL-1004]], with `prompt.md` beside it:
    the final prompt; the service and model; every parameter from step
    5; the job id the service returned; the path of every reference;
    whether this was the default path or a named exception; the variant
    picked and why. With that file anyone can make the image again. An
    image bound for another person goes through Vera's quality gate
    first when her pack is installed. Filing it into the user's Assets
    is Penn's step.

A prompt pattern worth keeping, and what the user picked, goes into
Pixel's `Journal/`; the session itself is logged by Larry at close.
