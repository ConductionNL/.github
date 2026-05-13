# Dutch (nl) translation skeleton

Skeleton for the Nederlandse vertaling of `docs.conduction.nl`. Docusaurus
falls back to English for any string not yet translated, so this directory
can be expanded incrementally without breaking the live site.

## What's here

- `code.json` — theme-level UI strings (back-to-top button, 404 page,
  breadcrumbs, sidebar collapse/expand, last-updated, edit-this-page, …).
- `docusaurus-theme-classic/navbar.json` — navbar item labels.
- `docusaurus-theme-classic/footer.json` — footer link column titles and labels.
- `docusaurus-plugin-content-docs/current.json` — sidebar category labels.

## What's still missing (intentionally)

Per-page Dutch translations of the markdown under `.github/docs/` —
each `docs/<path>.md` would get a sibling at
`i18n/nl/docusaurus-plugin-content-docs/current/<path>.md`. Adding the
files is incremental: untranslated routes fall back to the English source.

## Refreshing the keys

If the English navbar/footer/sidebar labels change, regenerate the JSON
key shape with:

```sh
npm run docusaurus -- write-translations --locale nl
```

Then re-add the Dutch `message` values (write-translations seeds the key
with the English text by default).
