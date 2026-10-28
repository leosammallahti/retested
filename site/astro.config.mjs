import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';
import sitemap from '@astrojs/sitemap';
import fs from 'node:fs';

// Effect pages without a replication of their own are noindex (see linkedEffects in src/lib/data.ts), so they stay out
// of the sitemap too; the same rule, read from the same built file.
const unlinked = new Set(
  JSON.parse(fs.readFileSync(new URL('../data/build/effects.json', import.meta.url), 'utf8'))
    .filter((e) => e.attempts.length === 0).map((e) => e.slug),
);

// SITE / BASE come from CI for GitHub Pages; local dev serves at /.
export default defineConfig({
  site: process.env.SITE_URL || 'https://retested.science',
  base: process.env.BASE_PATH || '/',
  trailingSlash: 'always',
  integrations: [
    preact(),
    sitemap({
      // Result dossiers are deliberately separate anti-spoiler documents.
      // Their canonical prediction pages belong in search and the sitemap.
      filter: (page) => {
        const path = new URL(page).pathname;
        if (/\/finding\/[^/]+\/result\/$/.test(path) || /\/not-linked\/$/.test(path)) return false;
        const m = path.match(/\/effect\/([^/]+)\/$/);
        return !(m && unlinked.has(decodeURIComponent(m[1])));
      },
    }),
  ],
  build: { format: 'directory' },
  server: { port: 4321 },
});
