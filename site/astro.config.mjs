import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';
import sitemap from '@astrojs/sitemap';

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
      filter: (page) => !/\/finding\/[^/]+\/result\/$/.test(new URL(page).pathname),
    }),
  ],
  build: { format: 'directory' },
  server: { port: 4321 },
});
