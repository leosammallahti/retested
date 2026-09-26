import type { APIRoute } from 'astro';

export const prerender = true;

export const GET: APIRoute = ({ site }) => {
  const origin = site ?? new URL('https://retested.science');
  const base = import.meta.env.BASE_URL.replace(/^\/+|\/+$/g, '');
  const sitemap = new URL(`${base ? `${base}/` : ''}sitemap-index.xml`, origin);
  return new Response(`User-agent: *\nAllow: /\n\nSitemap: ${sitemap.href}\n`, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};
