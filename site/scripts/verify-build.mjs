import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(SITE, 'dist');
const BUILD = path.resolve(SITE, '..', 'data', 'build');
const base = normalizeBase(process.env.BASE_PATH || '/');

function fail(message) {
  throw new Error(`Static build verification failed: ${message}`);
}

function normalizeBase(value) {
  const start = value.startsWith('/') ? value : `/${value}`;
  return start.endsWith('/') ? start : `${start}/`;
}

function walk(dir, suffix) {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...walk(full, suffix));
    else if (!suffix || entry.name.endsWith(suffix)) files.push(full);
  }
  return files;
}

function pageUrl(file) {
  const rel = path.relative(DIST, file).split(path.sep).join('/');
  if (rel === 'index.html') return base;
  if (rel.endsWith('/index.html')) return `${base}${rel.slice(0, -'index.html'.length)}`;
  return `${base}${rel}`;
}

function targetFile(pathname) {
  if (!pathname.startsWith(base)) return null;
  let rel;
  try {
    rel = decodeURIComponent(pathname.slice(base.length));
  } catch {
    return null;
  }
  const candidates = pathname.endsWith('/')
    ? [path.join(DIST, rel, 'index.html')]
    : [path.join(DIST, rel), path.join(DIST, rel, 'index.html')];
  return candidates.find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile()) || null;
}

if (!fs.existsSync(DIST)) fail('site/dist is missing; run the Astro build first');

const findings = JSON.parse(fs.readFileSync(path.join(BUILD, 'findings.json'), 'utf8'));
const findingRows = Object.values(findings);
if (!findingRows.length) fail('the finding registry is empty');

let findingPages = 0;
for (const finding of findingRows) {
  if (!finding.slug) fail(`finding ${finding.doi_o || '(unknown DOI)'} has no slug`);
  if (finding.page !== true) fail(`finding ${finding.doi_o} is not marked for a local page`);
  const file = path.join(DIST, 'finding', finding.slug, 'index.html');
  if (!fs.existsSync(file)) fail(`missing finding page ${finding.slug}`);
  const html = fs.readFileSync(file, 'utf8');
  if (!html.includes('What do you expect this record to show?')) fail(`finding ${finding.slug} has no prediction prompt`);
  if (!html.includes('generated/finding/r/')) fail(`finding ${finding.slug} has no separated reveal URL`);
  if (/record(?:Code|Label)|full-replication-record|class="ledger"|class="verdict rise"/.test(html)) fail(`finding ${finding.slug} embeds result data before reveal`);
  const revealFile = path.join(DIST, 'generated', 'finding', 'r', `${finding.slug}.json`);
  if (!fs.existsSync(revealFile)) fail(`missing finding reveal ${finding.slug}`);
  const reveal = JSON.parse(fs.readFileSync(revealFile, 'utf8'));
  const expected = finding.lenses.record;
  if (reveal.schema_version !== 1 || reveal.record?.code !== expected.code || reveal.record?.label !== expected.label
      || reveal.record?.n_attempts !== expected.n_attempts || reveal.record?.successful !== expected.successful
      || reveal.record?.mixed !== expected.mixed || reveal.record?.failed !== expected.failed) {
    fail(`finding reveal ${finding.slug} does not match its built record`);
  }
  const resultFile = path.join(DIST, 'finding', finding.slug, 'result', 'index.html');
  if (!fs.existsSync(resultFile)) fail(`missing full finding result page ${finding.slug}`);
  const resultHtml = fs.readFileSync(resultFile, 'utf8');
  if (!resultHtml.includes('Full source and attempt record')) fail(`finding result ${finding.slug} has no dossier`);
  if (!/<meta name="robots" content="noindex, follow"/.test(resultHtml)) fail(`finding result ${finding.slug} is indexable`);
  findingPages++;
}

const search = JSON.parse(fs.readFileSync(path.join(DIST, 'generated', 'search.json'), 'utf8'));
const searchFindings = search.filter((entry) => entry.t === 'finding');
if (searchFindings.length !== findingRows.length) fail(`search has ${searchFindings.length} findings; expected ${findingRows.length}`);
if (searchFindings.some((entry) => 'c' in entry || 'pg' in entry)) fail('finding search entries expose an outcome or obsolete page gate');
const contextTiers = new Set([
  'source_reviewed_explanation', 'plain_language_game_context', 'fallback_source_reviewed_claim',
  'fallback_forrt_coded_claim', 'fallback_named_effect', 'fallback_title_only', 'no_context',
]);
if (searchFindings.some((entry) => !contextTiers.has(entry.ctx))) fail('finding search entries have a missing or invalid context tier');
const stats = JSON.parse(fs.readFileSync(path.join(BUILD, 'stats.json'), 'utf8'));
const reviewedSearch = searchFindings.filter((entry) => entry.ctx === 'source_reviewed_explanation').length;
if (reviewedSearch !== stats.finding_context_coverage?.source_reviewed_explanation) {
  fail(`search has ${reviewedSearch} source-reviewed findings; stats report ${stats.finding_context_coverage?.source_reviewed_explanation}`);
}

const htmlFiles = walk(DIST, '.html');
const indexPages = htmlFiles.filter((file) => path.basename(file) === 'index.html').length;
const indexablePages = htmlFiles.filter((file) => path.basename(file) === 'index.html'
  && !/<meta name="robots" content="noindex\b/i.test(fs.readFileSync(file, 'utf8'))).length;
const sitemap = fs.readFileSync(path.join(DIST, 'sitemap-0.xml'), 'utf8');
const sitemapUrls = (sitemap.match(/<url>/g) || []).length;
if (sitemapUrls !== indexablePages) fail(`sitemap has ${sitemapUrls} URLs; expected ${indexablePages} indexable pages (${indexPages} total)`);

const idCache = new Map();
function idsFor(file) {
  if (!idCache.has(file)) {
    const html = fs.readFileSync(file, 'utf8');
    idCache.set(file, new Set([...html.matchAll(/\bid=["']([^"']+)["']/g)].map((match) => match[1])));
  }
  return idCache.get(file);
}

let localReferences = 0;
for (const file of htmlFiles) {
  const html = fs.readFileSync(file, 'utf8');
  const source = new URL(pageUrl(file), 'https://local.invalid');
  // Inline JavaScript can contain HTML-looking template strings. Keep each
  // script tag (and its src), but exclude its program text from attribute scans.
  const markup = html.replace(/(<script\b[^>]*>)[\s\S]*?<\/script>/gi, '$1</script>');
  const tags = [...markup.matchAll(/<[a-z][^>]*>/gi)].map((match) => match[0]);
  const urls = tags.flatMap((tag) => [...tag.matchAll(/\b(?:href|src)=["']([^"']+)["']/g)].map((match) => match[1]));
  for (const raw of urls) {
    if (/^(?:data|mailto|tel|javascript):/i.test(raw)) continue;
    let target;
    try {
      target = new URL(raw, source);
    } catch {
      fail(`invalid URL ${raw} in ${path.relative(DIST, file)}`);
    }
    if (target.origin !== source.origin) continue;
    localReferences++;
    if (!target.pathname.startsWith(base)) fail(`unbased local URL ${raw} in ${path.relative(DIST, file)}`);
    const resolved = targetFile(target.pathname);
    if (!resolved) fail(`missing local target ${raw} from ${path.relative(DIST, file)}`);
    if (target.hash) {
      let fragment;
      try {
        fragment = decodeURIComponent(target.hash.slice(1));
      } catch {
        fail(`invalid fragment ${raw} in ${path.relative(DIST, file)}`);
      }
      if (fragment && !idsFor(resolved).has(fragment)) fail(`missing fragment ${raw} from ${path.relative(DIST, file)}`);
    }
  }
}

console.log(JSON.stringify({
  base,
  html_pages: htmlFiles.length,
  indexable_pages: indexablePages,
  sitemap_urls: sitemapUrls,
  finding_pages: findingPages,
  local_references: localReferences,
  missing_targets: 0,
  missing_fragments: 0,
}, null, 2));
