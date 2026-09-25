---
type: guideline
id: GL-1005
title: Code vs instructions - the law
created: 2026-08-27
source: "myICOR article: Code Without Becoming a Coder"
---

# GL-1005 Code vs instructions: the law

> **Code for anything a machine could tell you got wrong. Instructions
> only for what a machine could not.**

An instruction is a request, re-decided by whichever model reads it, on
every run. A script returns the same answer every time and costs nothing
to run. Prose is the wrong material for any rule a machine can check.

## The sorting test, per step

Could a machine tell, definitively, whether this step was done right?

- **Yes -> deterministic work -> a script in `Scripts/` does it.**
  Naming, filing, moving, date math, format checks, frontmatter stamps,
  folder placement, archive moves.
- **No -> judgement work -> prose instructs the model.** What a
  scratchpad section IS, which topic something belongs to, what matters,
  how to word an expansion.

You do not choose one material per SOP. You choose per STEP, every time.

## The five standing rules

1. Never ask a model for something a script already answers.
2. SOPs mark each step [JUDGEMENT] or [SCRIPT]; script steps are thin
   pointers, the script is the source of truth.
3. A bad outcome gets answered with a check, never a better sentence.
   The rule broken today becomes the script that cannot break tomorrow.
4. Every guard is red-tested: feed it something it must reject and watch
   it actually say no. Never ship a gate you have not watched go red.
   `Scripts/run-red-tests.py` does this on demand.
5. Instruction files should shrink over time as prose rules graduate
   into code. Judgement rules stay prose forever, and that is correct.

## For the user

You never need to open `Scripts/`. Describe a rule in plain words; the
AI writes and maintains the script. You are the architect, not the
typist.
