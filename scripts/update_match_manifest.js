#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const matchesDir = path.join(repoRoot, 'viewer', 'matches');
const manifestPath = path.join(matchesDir, 'manifest.json');

if (!fs.existsSync(matchesDir)) {
  fs.mkdirSync(matchesDir, { recursive: true });
}

const matches = fs
  .readdirSync(matchesDir, { withFileTypes: true })
  .filter((entry) => entry.isFile())
  .map((entry) => entry.name)
  .filter((name) => name.endsWith('.json') && name !== 'manifest.json')
  .sort((a, b) => a.localeCompare(b))
  .map((fileName) => ({
    label: formatLabel(fileName),
    path: `matches/${fileName}`
  }));

const manifest = {
  version: 1,
  updated_at: new Date().toISOString(),
  matches
};

fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
console.log(`Updated ${path.relative(repoRoot, manifestPath)} with ${matches.length} entr${matches.length === 1 ? 'y' : 'ies'}.`);

function formatLabel(fileName) {
  const base = fileName.replace(/\.json$/i, '');
  const withSpaces = base.replace(/[_-]+/g, ' ');
  return withSpaces.replace(/\b\w/g, (char) => char.toUpperCase());
}
