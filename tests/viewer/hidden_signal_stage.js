#!/usr/bin/env node

const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..', '..');
const stageRoot = path.join(repoRoot, 'research/references/hidden-signal/stage');
const stage = require(path.join(stageRoot, 'stage.js'));
const canonical = path.join(stageRoot, 'canonical');
const manifest = JSON.parse(fs.readFileSync(path.join(canonical, 'manifest.json'), 'utf8'));
const surface = JSON.parse(
  fs.readFileSync(path.join(canonical, manifest.match_surface), 'utf8')
);

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

stage.validateManifest(manifest);
stage.validateSurface(surface);
assert.strictEqual(sha256(path.join(canonical, manifest.record)), manifest.record_sha256);
assert.strictEqual(
  sha256(path.join(canonical, manifest.match_surface)),
  manifest.match_surface_sha256
);

const replay = stage.buildReplay(surface);
assert.strictEqual(replay.length, 3);
assert.strictEqual(stage.displaySignal(replay[0].state), 'HIDDEN');
assert.strictEqual(stage.frameProjection(replay[0]).action, 'Waiting');
assert.strictEqual(stage.frameProjection(replay[1]).action, 'INSPECT');
assert.strictEqual(stage.frameProjection(replay[1]).signal, surface.frames[0].state_after.signal);
assert.strictEqual(stage.frameProjection(replay[2]).choice, surface.frames[1].state_after.choice);
assert.strictEqual(stage.frameProjection(replay[2]).done, true);
assert.strictEqual(surface.match.winner, null);

console.log('hidden signal stage OK', {
  match: surface.match.match_id,
  steps: replay.length,
  label: manifest.label
});
