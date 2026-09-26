import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';
import sitemap from '@astrojs/sitemap';

// SITE / BASE come from CI for GitHub Pages; local dev serves at /.
export default defineConfig({
  site: process.env.SITE_URL || 'https://retested.science',
  base: process.env.BASE_PATH || '/',
  trailingSlash: 'always',
  integrations: [preact(), sitemap()],
  build: { format: 'directory' },
  server: { port: 4321 },
});
