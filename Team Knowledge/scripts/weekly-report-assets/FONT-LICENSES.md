# Bundled fonts - attribution and licence

`inkline-fonts.css` embeds four webfonts as base64 so a rendered weekly edition
opens correctly from `file://` with zero external requests.

**All four are licensed under the SIL Open Font License, Version 1.1**, which
permits embedding, modification and redistribution. Each font's own `name` table
carries its `license_url` pointing at <https://scripts.sil.org/OFL>; the full
licence text is reproduced by reference below because the web-subsetting step
strips the embedded licence field (nameID 13) to save bytes.

| Font | Copyright | Upstream project |
|---|---|---|
| Bricolage Grotesque | Copyright 2022 The Bricolage Grotesque Project Authors | <https://github.com/ateliertriay/bricolage> |
| Instrument Sans | Copyright 2022 The Instrument Sans Project Authors | <https://github.com/Instrument/instrument-sans> |
| Caveat | Copyright 2014 The Caveat Project Authors | <https://github.com/googlefonts/caveat> |
| Spline Sans Mono | Copyright 2022 The Spline Sans Mono Project Authors | <https://github.com/SorkinType/SplineSansMono> |

## What the OFL requires of us, and how we satisfy it

1. **The copyright notice travels with the fonts.** That is this file. Keep it
   next to `inkline-fonts.css`; do not ship the CSS without it.
2. **The fonts are not sold on their own.** They are not. They ship as part of a
   rendering asset set and carry no separate charge.
3. **No Reserved Font Name is claimed or reused.** None of the four declares an
   RFN, and we do not rename or re-release any of them as our own family.
4. **Derivatives stay under the OFL.** We embed the fonts unmodified apart from
   character-set subsetting, which the licence permits.

The OFL applies to these font binaries only. It does not change the licence of
the surrounding scaffold (CC BY-NC-SA 4.0, see `LICENSE-MAP.md`).

Full licence text: <https://openfontlicense.org/open-font-license-official-text/>
