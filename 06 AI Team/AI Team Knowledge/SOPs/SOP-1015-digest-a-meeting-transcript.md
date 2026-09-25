---
type: sop
id: SOP-1015
title: Digest a meeting transcript
created: 2026-09-09
owner: penn
uses: ["[[GL-1002-frontmatter-conventions]]", "[[GL-1007-capture-and-where-things-go]]", "[[GL-1010-the-five-capture-workflows]]", "[[SOP-1004-create-or-update-a-my-life-entity]]", "[[SOP-1005-create-or-update-a-contact]]"]
---

# SOP-1015 Digest a meeting transcript

## Purpose

Turn a transcript from any tool into the part of a meeting note that is
worth keeping. Runs when the member says "digest this meeting", "what did I
commit to", "enrich my notes from the transcript", or names a meeting and a
transcript in one sentence.

**The Scaffold does not record meetings** ([[GL-1010-the-five-capture-workflows|GL-1010]],
workflow 4). The member brings a transcript from Wispr Flow, Granola,
Otter, Fireflies or anything else. This procedure is tool-agnostic on
purpose: it takes text and a steer, and returns note content.

## Inputs

Three, and only the first is mandatory:

1. **The transcript.** A URL in the member's tool, a file in `concept:assets`,
   a note that came through `concept:inbox/outer_world`, or pasted text. Read it
   from wherever it is; if it comes from a connected tool, pull it through
   that tool's own connection rather than asking the member to paste.
2. **The steer.** What the member wants out of it. If they did not say, ask
   once, in one line, and offer the three that are almost always right:
   what was decided, what I committed to, what I still owe an answer on.
3. **The member's own notes**, when they wrote any. These outrank the
   transcript everywhere the two disagree about what mattered.

## 1. Find or create the meeting note

[JUDGEMENT] One meeting, one note, in `concept:notes` with
`note_type: meeting`. If the member already wrote one, use it; never make a
second. If none exists, create it from `Templates/note`.

Set `transcript` to wherever the transcript actually is, and
`transcribed_by` to the tool's name in the words the member would say out
loud (`Wispr Flow`, not a model id). Both per
[[GL-1002-frontmatter-conventions|GL-1002]] §Meeting notes.

## 2. Read the transcript against the steer

[JUDGEMENT] Not a summary. A summary of a meeting is a thing nobody reads,
and producing one is the most common way this procedure fails. Extract only
what the steer asked for, plus anything that is unambiguously a decision or
a commitment the member made out loud.

Three things earn their place in a meeting note:

- **Decisions.** What was settled, and by whom, and what it rules out.
- **Commitments.** What the member said they would do, in their own words
  where possible, and what other people committed to them.
- **Open loops.** Questions raised and not answered, objections not
  addressed. These are the most valuable and the most often lost, because
  nothing in the transcript marks them.

## 3. Enrich rather than replace

[JUDGEMENT] When the member wrote their own notes, their words stay exactly
as written. Add context around them: what a fragment referred to, who said
the thing they reacted to, the number they half-remembered. Mark clearly
where the transcript contradicts what they wrote; do not silently correct
them, because their memory of the room is evidence too.

Never paraphrase the member's own sentences. Never merge their line and
yours into one sentence.

## 4. Link it

[JUDGEMENT] The link rule holds: at least one of `projects`,
`key_elements`, `topics`. Add `people` for everyone who was actually in the
room, creating contact notes only per [[SOP-1005-create-or-update-a-contact|SOP-1005]]
and entity notes only per [[SOP-1004-create-or-update-a-my-life-entity|SOP-1004]].
A person mentioned in passing is not an attendee.

## 5. Record who wrote it

[SCRIPT] Set `ai_summary` to the model id of the run that produced the
block, for example `claude-opus-5`. A reader has to be able to answer
"which model wrote this" from the field alone.

Mark the AI-written part of the body so it is distinguishable from what the
member wrote. The member's words and the model's words are not the same
kind of evidence and the note should never blur them.

## 6. Actions leave the vault

[JUDGEMENT] Every action item goes to the member's task manager, not into
this note as a checkbox. The note records that a commitment was made; the
task manager is where it gets done. That is workflow 6 and it is not this
vault's job.

## 7. Report

Say what was added, in one short list, with the note's link. Name anything
the transcript raised that you deliberately left out, so the member can
overrule you in one sentence.

## What this procedure never does

- Start, stop or store a recording. The Scaffold does not record.
- Ask for consent on the member's behalf. Whatever their transcriber asks,
  and whatever the law where they and the other people are, is between them
  and the room.
- Write a full summary of the meeting when nobody asked for one.
- Create a second note for a meeting that already has one.
