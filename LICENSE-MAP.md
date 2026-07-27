# myPKA License Map

**In one sentence:** Use myPKA for anything you like, including in and for your
business, and share it freely. What you may not do is sell it or pass it off as
your own product.

This file is a plain-language guide. The binding terms are in each subtree's own
`LICENSE` file. Where this guide and a `LICENSE` differ, the `LICENSE` wins.

---

## What governs what

| Subtree | License | © Holder | You MAY | You MAY NOT |
|---|---|---|---|---|
| **Base scaffold** (root markdown: PKM, Team, Team Knowledge, SOPs, etc.) | CC BY-SA 4.0 | Paperless Movement S.L. | Edit, adapt, and customize it. Run it with any LLM. Use it for any purpose, **including commercially and inside your own business or client work**. Share it. | Drop the attribution. Relicense a shared adaptation under different terms (ShareAlike keeps it open). Use our trademarks to brand it. |
| **Cockpit runtime** (`Expansions/mypka-cockpit/`) | PolyForm Noncommercial 1.0.0 (adapted: "myICOR Cockpit Personal-Use License") | myICOR | Download, run, read, study, and modify the source (including with your own LLM), and share your changes, for personal, non-commercial use. | Sell it, sublicense it for a fee, or run it as a paid product or hosted service for others. |

**Expansion Packs are licensed separately.** Agent packs you download from the
myICOR Expansion Packs page (the Designer Pack, the App Developer Pack, and
others) are not part of this repository and are not covered by this map. Each
pack carries its own terms; read them on install.

**Common thread for what is in this repository:** edit it freely, use it at work,
share it. Credit us, keep shared adaptations open, and do not brand it as your
own product. The Cockpit runtime is the one exception in the table above: it
stays non-commercial.

---

## Can I use myPKA in my business?

**Yes.** Consultants, coaches, agencies, and teams may run myPKA on client work
and inside a commercial operation. That is an intended use, not a tolerated one.

Two things still apply. **Attribution:** anything you share publicly credits the
myPKA™ Scaffold by Paperless Movement® / ICOR®. **ShareAlike:** if you publicly
distribute an adapted version, that version carries CC BY-SA 4.0 too, so it stays
as open as you received it. Neither of those stops you using it to earn a living.

What is not permitted is taking myPKA, closing it, branding it as your own
invention, and selling it as a proprietary product. Attribution and ShareAlike
prevent that on the copyright side; the trademarks prevent it on the branding
side.

The Cockpit runtime is the one exception in this table: it stays non-commercial.

---

## What changed, and what it does not reach

The base scaffold moved from **CC BY-NC-SA 4.0** to **CC BY-SA 4.0**. The
NonCommercial term is gone. Attribution and ShareAlike are unchanged, and the
trademark reservation is unchanged.

The NonCommercial term was doing the wrong job. It blocked members from using
myPKA in their own work, which was never the intent, while doing nothing to stop
someone rebranding it. Attribution, ShareAlike, and trademark do that job
properly.

**This does not reach existing copies.** Creative Commons licenses are
irrevocable. Every copy downloaded before this change, and every fork of one,
stays licensed under CC BY-NC-SA 4.0 permanently. Nothing is withdrawn from
anyone. The new terms are strictly more permissive and apply going forward, so if
you hold an older copy you may simply take the new terms for a new copy.

---

## Trademarks (NOT licensed by any of the above)

The licenses above cover copyrightable text and structure only. Per CC BY-SA 4.0
Section 2(b)(2), no trademark or patent rights are granted. These marks are owned
by Paperless Movement S.L. and/or its affiliated holding entity:

- **PAPERLESS MOVEMENT®** - USPTO Reg. No. 6,689,873
- **ICOR®** - USPTO Reg. Nos. 6,607,819 and 6,608,200
- **myICOR™**, **myPKA™** - common-law / EUTM pending

You may name them descriptively (e.g. "based on the myPKA™ Scaffold by ICOR®").
You may not use them to brand a derivative or competing product. Full guidance in
`TRADEMARK.md`.

---

## One bundled dependency to be aware of (inert)

The Cockpit lists `react-leaflet` and `@react-leaflet/core` under the
**Hippocratic License 2.1** (an "ethical-source", non-OSI license). These are used
**only** by the optional `workouts` feature pack, which ships as **inert source**
and is **not compiled into the core application** unless a user explicitly
activates it. As distributed, the core Cockpit executes no Hippocratic-licensed
code. If you activate the workouts pack and distribute the result, you must
preserve the Hippocratic 2.1 text and honor its conditions for those portions.
Full detail in `Expansions/mypka-cockpit/NOTICE`.

---

This is compliance analysis (Einschätzung im Sinne des § 6 RDG), not legal advice
(keine Rechtsberatung). For binding legal opinions, consult a licensed Fachanwalt
in the relevant jurisdiction.
