# ADCPortal wiki backup

A static, read-only preservation copy of the old **ADCPortal wiki** (`adcportal.com`), the
documentation hub for the ADC (Advanced Direct Connect) protocol. The original MediaWiki
site went offline after 2011; this repository reconstructs it from Internet Archive
snapshots and serves it as a self-contained static site.

Live copy: [https://adcpwiki.dcvault.net](https://adcpwiki.dcvault.net/)

## What this is

The wiki was captured by the Wayback Machine mainly in September and October 2011, shortly
before it stopped serving real content (redirects from late 2011, domain parking by 2015,
404 by 2016). Each page here uses its newest genuine capture, merged from all snapshots into
the most complete version possible. Nothing newer exists in the archive.

In addition, 64 pages that the Wayback Machine never captured were recovered from a
community database backup of the wiki (the original wikitext as of February 2011), provided
by a former admin. They were rendered back to HTML with a local MediaWiki (so templates and
infoboxes expand) and reskinned to match the rest of the archive. These pages carry their own
footer note. That backup holds no image binaries, so images on recovered pages show as
placeholders. Three pages that once existed (BNF, NetChatLink, Violating Distribution Sites)
survive in neither source and remain as inactive links.

The reconstruction keeps the original MediaWiki Vector appearance: the original skin CSS
(`main-ltr.css`, `shared.css`) and the site's own `MediaWiki:Common.css` / `Vector.css` /
`gen.css` were recovered from the archive and are served locally. Wayback toolbar injection
is stripped, internal links are rewritten to local pages, and interactive chrome (search,
edit, login) is inert.

## Honest gaps

- 48 pages were linked but never captured with a real (HTTP 200) snapshot, so they cannot be
  recovered. Links to them are shown in red with a "Page not archived" tooltip.
- A few images (some small skin icons and two diagrams) were never captured and show as
  placeholders.
- Only the article view is preserved, not the per-page edit/talk history.

## Layout

- `site/` — the deployable static wiki (Cloudflare Pages output directory, no build step).
- `raw/` — pristine originals pulled from the Wayback Machine (the actual backup) plus the
  build manifests (`*.json`).
- `tools/` — the Python scripts used to fetch and reconstruct the site. They use absolute
  paths from the original build machine; adjust the `RAW`/`SITE` constants to re-run.

## Deploying

The site is plain static HTML with no build step. On Cloudflare Pages, set the build output
directory to `site/` and leave the build command empty. Manual deploy:

    npx wrangler pages deploy site --project-name adcportal-wiki-backup

## License and attribution

The wiki content is licensed under the **GNU Free Documentation License 1.2**, as on the
original site. This repository is an independent community preservation copy and is not
affiliated with the original operators of `adcportal.com`.
