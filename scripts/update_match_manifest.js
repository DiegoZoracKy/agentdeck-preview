#!/usr/bin/env node

const fs = require('fs')
const path = require('path')

const repoRoot = path.join(__dirname, '..')
const matchesDir = path.join(repoRoot, 'viewer', 'matches')
const manifestPath = path.join(matchesDir, 'manifest.json')
const MatchMetadataUtils = require(path.join(repoRoot, 'viewer/js/match-metadata.js'))

if (!fs.existsSync(matchesDir)) {
  fs.mkdirSync(matchesDir, { recursive: true })
}

const existingManifest = readJson(manifestPath)
const existingEntries = MatchMetadataUtils.normalizeManifestEntries(existingManifest || {})
const existingByPath = new Map(existingEntries.map((entry) => [entry.path, entry]))

const fileNames = fs
  .readdirSync(matchesDir, { withFileTypes: true })
  .filter((entry) => entry.isFile())
  .map((entry) => entry.name)
  .filter((name) => name.endsWith('.json') && name !== 'manifest.json' && !name.endsWith('.meta.json'))
  .sort((a, b) => a.localeCompare(b))

const discoveredPaths = fileNames.map((fileName) => `matches/${fileName}`)
const discoveredSet = new Set(discoveredPaths)
const orderedPaths = [
  ...existingEntries.map((entry) => entry.path).filter((matchPath) => discoveredSet.has(matchPath)),
  ...discoveredPaths.filter((matchPath) => !existingByPath.has(matchPath))
]

const matches = orderedPaths.map((matchPath) => {
  const fileName = path.basename(matchPath)
  const existingEntry = existingByPath.get(matchPath)
  const baseEntry = {
    label: existingEntry ? existingEntry.label : formatLabel(fileName),
    path: matchPath
  }

  const sidecarPath = path.join(matchesDir, fileName.replace(/\.json$/i, '.meta.json'))
  const sidecar = readJson(sidecarPath)
  if (!sidecar) {
    return baseEntry
  }
  return MatchMetadataUtils.mergeEntryWithMetadata(baseEntry, sidecar)
})

const manifest = {
  version: 1,
  updated_at: new Date().toISOString(),
  matches
}

fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
console.log(
  `Updated ${path.relative(repoRoot, manifestPath)} with ${matches.length} entr${
    matches.length === 1 ? 'y' : 'ies'
  }.`
)

function readJson(filePath) {
  if (!fs.existsSync(filePath)) return null
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'))
  } catch (err) {
    console.warn(`Skipping invalid JSON: ${path.relative(repoRoot, filePath)} (${err.message})`)
    return null
  }
}

function formatLabel(fileName) {
  const base = fileName.replace(/\.json$/i, '')
  const withSpaces = base.replace(/[_-]+/g, ' ')
  return withSpaces.replace(/\b\w/g, (char) => char.toUpperCase())
}
