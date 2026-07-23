# Outer World — capture-time embed fetcher

Item 10 ("Outer World"): when Tom saves external content into his myPKA, the
embed metadata is fetched **at capture time** (by the LLM/Larry, who has network
access at save time) and stored in the note's **flat `embed_*` frontmatter**. The
cockpit later renders a **static rich card OFFLINE** from that frontmatter — it
never touches the network at view time.

This document covers the fetcher: `scripts/fetch-embed.mjs`.

> **This is NOT a cockpit-runtime dependency.** Nothing in `server/` or `web/`
> imports it. It runs once, at save time, on the command line. The cockpit only
> ever reads the resulting frontmatter (and the localized image file).

---

## Usage

```sh
node scripts/fetch-embed.mjs "<url>" [--no-localize] [--json] [--note <slug>]
```

| Flag            | Effect |
|-----------------|--------|
| (default)       | Localizes the preview image into `PKM/Images/YYYY/MM/` and sets `embed_image` to that `PKM/`-relative path. |
| `--no-localize` | Skips the image download; keeps the remote **https** URL in `embed_image` (or `null` if non-https). |
| `--json`        | Emits a JSON object instead of a YAML frontmatter block. |
| `--note <slug>` | Slug for the localized image filename (`YYYY-MM-DD-<slug>-embed.<ext>`). Defaults to the domain. |

Run with no arguments (or an invalid URL) and it still emits a **minimal card**
(kind `link` + `source_url`) rather than erroring — graceful degradation is the
contract.

---

## Invocation contract (for the install / capture docs)

> **To save any social or article URL as an Outer World item, run
> `node scripts/fetch-embed.mjs <url>`.** It extracts the content via
> **oEmbed / OG with no login and no browser**.
> **NEVER** plain-`fetch` a social URL (X tweet pages are auth-walled → HTTP 402)
> and **NEVER** open Chrome to read one. **NEVER** store raw embed HTML,
> blockquotes, or `<script>` — store only the extracted text and the `embed_*`
> fields the script emits.

This snippet is the authoritative one-liner Marshall surfaces in the install and
capture documentation. It exists because the original capture flow plain-fetched
an X URL, hit a 402 auth wall, and wrongly fell back to opening a browser — the
fetcher now removes both the need to authenticate and the temptation to browse.

---

## How the capture flow (Larry, at save time) invokes it

This is the step the LLM performs when Tom saves a link as an Outer World note:

1. **Run the fetcher** against the saved URL, choosing a slug from the note title:

   ```sh
   node scripts/fetch-embed.mjs "https://example.com/some-article" --note some-article
   ```

2. **Take the emitted `embed_*` block** and splice it into the new note's YAML
   frontmatter (alongside whatever other frontmatter Silas's Outer World note
   template defines — `title`, `tags`, etc.).

3. **The localized image** already sits under `PKM/Images/YYYY/MM/`. The cockpit
   serves it via its existing read-only media route
   (`/api/cockpit/media?path=Images/YYYY/MM/...`), so the offline card just points
   at the `embed_image` path. No further wiring needed.

4. **Done.** The note is now self-contained: the cockpit renders the card with
   zero network calls.

For programmatic callers, `--json` returns the same fields as an object, and the
module exports `buildEmbed(url, opts)` / `classifyEmbedUrl(url)` for reuse (the
CLI only runs when the file is invoked directly, not on import).

---

## Output frontmatter shape (matches Silas's flat field names)

```yaml
embed_kind: "video"          # article | post | video | image | link
embed_title: "…"             # TEXT, ≤ 200 chars, or null
embed_description: "…"       # TEXT, ≤ 500 chars, or null
embed_image: "Images/2026/06/2026-06-18-some-article-embed.jpg"  # PKM/-relative local path, OR remote https URL, OR null
embed_site_name: "YouTube"   # TEXT or null
embed_domain: "youtube.com"  # canonical host, www-stripped
embed_favicon: "https://…"   # https(s) URL or null (never a data: URI)
embed_author: "Rick Astley"  # TEXT (author_name / @handle) or null
embed_captured_at: "2026-06-18T12:53:58Z"  # ISO-8601 UTC of this fetch
source_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
source_type: "outer_world"   # always this literal
```

`embed_image` is **`PKM/`-relative** (e.g. `Images/2026/06/x.jpg`) — the exact
convention the cockpit's `/api/cockpit/media` route already uses for journal
images (`journal_media.file_path` is also `PKM/`-relative). If localization fails
(non-https image, download error, parse fail, or the scaffold root can't be
resolved), `embed_image` falls back to the remote https URL, and if even that
isn't https, it is `null`.

---

## Classification — `embed_kind`

The classifier logic is **ported from myICOR**
`src/components/editor/tiptap/markdownRender.ts` (`classifyEmbedUrl` /
`EmbedClassification` / `matchVideoUrl` + the social regexes). The myICOR
taxonomy is richer (`tweet | video | internal | link | image | tiktok | linkedin
| instagram`); it is **mapped onto** the cockpit's Outer World taxonomy:

| URL shape | myICOR kind | → cockpit `embed_kind` |
|-----------|-------------|------------------------|
| YouTube / Vimeo / Loom | `video` | `video` |
| X/Twitter status, TikTok, LinkedIn post, Instagram | `tweet`/`tiktok`/`linkedin`/`instagram` | `post` |
| Direct image URL (`.png/.jpg/.gif/.webp/.avif/.svg`) | `image` | `image` |
| Page with `og:type` = article/news/blog | `link` | `article` |
| Anything else | `link` | `link` |

Ordering matters and mirrors myICOR: video → social/post → direct-image → generic
(article-or-link).

---

## Metadata fetch by kind

| Kind | Source | Notes |
|------|--------|-------|
| **generic / article** | OG/Twitter-card scrape | Algorithm ported from `supabase/functions/fetch-link-preview/index.ts`: `getMeta` precedence (`og:` → `name` → `twitter:`), `extractBestImage` ladder, `isValidImageUrl` tracking-pixel filter, title cap 200 / description cap 500. The DOM content-image strategies (article/main `<img>`) are dropped — there's no DOM library — but the meta/Twitter/schema/article/link-rel ladder is intact. |
| **YouTube** | `youtube.com/oembed?url=…&format=json` (no key) | → `title`, `author_name`, `thumbnail_url`. Thumbnail also constructed as `img.youtube.com/vi/<id>/hqdefault.jpg` fallback. |
| **Vimeo / Loom** | their public oEmbed endpoints (no key) | → title, description, author, thumbnail. |
| **X / Twitter** | official **oEmbed** — `publish.twitter.com/oembed?url=…&omit_script=1&dnt=true&hide_thread=true` (301→`publish.x.com`; `fetch` follows the redirect) | **NO auth, NO browser.** Returns JSON `{ html, author_name, author_url, provider_name }`. We extract **only the tweet `<p>` text** from `html` (all tags stripped, incl. any residual `<script>`), set `embed_author` from `author_name` (or the `@handle` parsed from the URL), `embed_site_name` from `provider_name` ("X"). `embed_image` is `null` — oEmbed exposes no card image without the widget script, and we never load it. **A plain `fetch` of the tweet page itself is auth-walled (HTTP 402) and must NEVER be attempted, nor must Chrome be opened.** The old OG-scrape path was the cause of the 402→browser-fallback failure. |
| **TikTok** | public **oEmbed** — `www.tiktok.com/oembed?url=…` | **NO token.** → title + author_name + thumbnail. Falls back to OG scrape if oEmbed fails. |
| **LinkedIn** | OG scrape → minimal honest card | oEmbed requires an authenticated LinkedIn app (no no-token path); the public post is frequently bot-walled. When OG yields nothing we emit a **minimal honest card**: `LinkedIn` + domain + an author derived from the URL slug. No fabricated content. |
| **Instagram** | OG scrape → minimal honest card | oEmbed now **requires a Facebook app access token** (`graph.facebook.com/.../instagram_oembed` → `OAuthException` without one; the legacy `api.instagram.com/oembed` is deprecated → login wall). When OG is login-walled we emit a **minimal honest card**: `Instagram` + domain + favicon + `@user` from the URL path if present. No fabricated content. |
| **direct image** | the URL itself is the image | Localized like any other preview image. |

---

## Security posture (Axon)

- **All fetched strings → inert TEXT.** `sanitizeText` strips HTML tags, decodes a
  small safe set of entities, removes control chars, collapses whitespace, and
  length-caps. No markup reaches the frontmatter, so the cockpit's offline card
  renders text only. Title cap 200, description cap 500.
- **Image URLs are https-only before download.** A non-https image is never
  fetched and never kept as a card image.
- **Favicon is http(s)-only** — `data:`/`blob:`/inline favicons are dropped
  (keeps the offline card's CSP clean; they're usually 1×1 junk anyway).
- **10s timeout per request; graceful degradation.** A bot-blocked / 404 / parse
  failure yields a minimal card (`embed_kind: link`, `embed_domain`, `source_url`)
  — the script **never throws** to the caller on a dead URL.
- **No third-party scripts, no npm deps.** Node stdlib + built-in `fetch` + a tiny
  hand-rolled meta-tag extractor. No DOM library, no `eval`.
- **Multiple User-Agents** (ported from `fetch-link-preview`) tried in order on
  403/429 to get past common bot walls.
- **Social URLs are NEVER plain-fetched.** A direct `fetch` of an X tweet page
  returns **HTTP 402** (auth wall); the old OG-scrape path tripped on this and
  wrongly fell back to opening a browser. The fix: social content comes from
  **oEmbed** (X, TikTok) or degrades to an OG-scrape / minimal honest card
  (LinkedIn, Instagram) — **never a plain page fetch and never a browser.**
- **oEmbed `html` is never stored.** For X we parse the blockquote, take only the
  `<p>` tweet text, and pass it through `sanitizeText`. The blockquote markup,
  the widget `<script>` (already suppressed by `omit_script=1`), and any
  smuggled `<script>`/`onerror`/`javascript:` are all stripped — the stored
  frontmatter can never contain executable markup. This is the exact failure the
  cockpit's `script-src 'self'` CSP caught when a stored raw embed tried to run;
  the fetcher now guarantees it can't happen at the source.

---

## Notes for the Vex image/CSP gate

When Silas wires the offline card renderer in `web/`, the card needs to display
**two** image sources:

1. **Localized images** — served from the existing read-only
   `/api/cockpit/media?path=Images/…` route (same-origin, `img-src 'self'`). This
   is the default and the safe path: bytes are on disk, already validated as
   `image/*` at download time, served with the cockpit's existing inert
   Content-Type + no-script CSP.
2. **Remote fallback images** — only present when localization failed. These are
   **https-only** by construction (the fetcher refuses non-https), so the card's
   `img-src` would need `https:` to display them. **Recommendation:** prefer
   localization (the default) so the card stays same-origin; treat the remote
   fallback as a degraded state, and if Vex wants a strict same-origin `img-src
   'self'` CSP, have the renderer **skip** rendering remote-URL `embed_image`
   values (fall back to favicon/text) rather than loosen the CSP. The fetcher
   already guarantees no `data:`/`blob:` URIs in `embed_image` or `embed_favicon`.

`embed_favicon` is also https-only and may be `null`. No inline data URIs anywhere
in the block.

---

## Ported-from (myICOR, read-only reference)

- myICOR codebase (private), `src/components/editor/tiptap/markdownRender.ts` —
  `classifyEmbedUrl`, `EmbedClassification`, `matchVideoUrl`, `DIRECT_IMAGE_RE`,
  and the X/TikTok/LinkedIn/Instagram regexes.
- myICOR codebase (private), `supabase/functions/fetch-link-preview/index.ts` —
  `getMeta` precedence, `extractBestImage` ladder, `isValidImageUrl` filter,
  title/description caps, multi-UA retry, YouTube/Loom oEmbed handling.

> **Divergence from myICOR (2026-06-18, Mack):** myICOR resolves X/Twitter and
> TikTok/LinkedIn/Instagram via server-side OG scraping. This standalone fetcher
> **does not** — a plain fetch of an X tweet page is auth-walled (402). X and
> TikTok now go through their official no-auth **oEmbed** endpoints; LinkedIn and
> Instagram degrade to OG-then-minimal-honest-card because their oEmbed requires a
> token. This is intentional and is the fix for the 402→browser-fallback failure.

---

## Known environmental quirk (handoff note)

The fetcher resolves the scaffold root by importing `REPO_ROOT` from
`server/repoRoot.js` (the cockpit's single resolver) so localized images land in
the exact `PKM/` the cockpit serves. **When the cockpit is run standalone (e.g.
on the Desktop, NOT installed inside a scaffold), `repoRoot.js` walks up and can
resolve `REPO_ROOT` to `$HOME`** — localized images then land in `~/PKM/Images/`.
This is a property of the cockpit's root resolution, not the fetcher. In a normal
in-scaffold install (`<scaffold>/Expansions/mypka-cockpit/`) it resolves
correctly. If running standalone, set `MYPKA_ROOT` to the intended scaffold root
before invoking, or pass `--no-localize` to keep remote https URLs.
