#!/usr/bin/env node

/**
 * Lightweight smoke-check for the browser replay viewer.
 *
 * Goals:
 * - Ensure the shipped sample record parses with RecordLoader.
 * - Ensure the sample game resolves to a registered renderer.
 * - Ensure Timeline can step through all frames and emits onEnd.
 *
 * This is intentionally not a full browser E2E test (no DOM required).
 */

const fs = require('fs');
const path = require('path');

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const repoRoot = path.join(__dirname, '..');

const RecordLoader = require(path.join(repoRoot, 'viewer/js/record-loader.js'));
const Timeline = require(path.join(repoRoot, 'viewer/js/timeline.js'));
const RendererRegistry = require(path.join(repoRoot, 'viewer/js/renderers/index.js'));
const FixedDamageFFVIRenderer = require(path.join(repoRoot, 'viewer/js/renderers/fixed_damage_ffvi.js'));

RendererRegistry.register('FixedDamageGame', FixedDamageFFVIRenderer);

const samplePath = path.join(repoRoot, 'viewer/sample-match.json');
const raw = JSON.parse(fs.readFileSync(samplePath, 'utf8'));

const matchData = RecordLoader.load(raw);
assert(matchData.game === 'FixedDamageGame', `Expected sample game to be FixedDamageGame, got ${matchData.game}`);
assert(Array.isArray(matchData.frames) && matchData.frames.length > 0, 'Expected sample to contain frames');

const renderer = RendererRegistry.create(matchData);
assert(renderer, 'RendererRegistry.create() returned falsy');

const timeline = new Timeline(matchData);
let frames = 0;
let ended = false;

timeline.onFrame(() => {
  frames += 1;
});
timeline.onEnd(() => {
  ended = true;
});

for (let i = 0; i < timeline.totalFrames; i += 1) {
  timeline.step(1);
}

assert(frames === timeline.totalFrames, `Expected ${timeline.totalFrames} frames, got ${frames}`);
assert(ended, 'Expected Timeline to emit onEnd after last frame');

console.log('viewer smoke-check OK', {
  schemaVersion: matchData.schemaVersion,
  game: matchData.game,
  frames
});

