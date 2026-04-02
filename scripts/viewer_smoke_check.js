#!/usr/bin/env node

/**
 * Lightweight smoke-check for the browser replay viewer.
 *
 * Goals:
 * - Ensure shipped local sample records parse with RecordLoader.
 * - Ensure bundled combat games resolve to registered renderers.
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
const CombatDebugRenderer = require(path.join(repoRoot, 'src/agentdeck/games/examples/fixed_damage/viewers/debug/renderer.js'));
const CombatRetroJrpgSceneRenderer = require(path.join(repoRoot, 'src/agentdeck/games/examples/fixed_damage/viewers/retro_jrpg_scene/renderer.js'));

RendererRegistry.register('FixedDamageGame', 'debug', CombatDebugRenderer);
RendererRegistry.register('FixedDamageGame', 'retro_jrpg_scene', CombatRetroJrpgSceneRenderer);
RendererRegistry.register('VariableDamageGame', 'debug', CombatDebugRenderer);
RendererRegistry.register('VariableDamageGame', 'retro_jrpg_scene', CombatRetroJrpgSceneRenderer);

const manifestPath = path.join(repoRoot, 'viewer/matches/manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
assert(Array.isArray(manifest.matches) && manifest.matches.length > 0, 'Expected viewer/matches/manifest.json to contain entries');
const validHighlightKinds = new Set(['mistake', 'smart_move', 'surprise', 'turning_point']);

function runSampleSmoke(entry, expectedGame) {
  assert(typeof entry.subtitle === 'string' && entry.subtitle.trim(), `Expected subtitle for ${entry.path}`);
  assert(typeof entry.synopsis === 'string' && entry.synopsis.trim(), `Expected synopsis for ${entry.path}`);
  assert(Array.isArray(entry.highlights) && entry.highlights.length > 0, `Expected highlights for ${entry.path}`);

  const samplePath = path.join(repoRoot, 'viewer', entry.path);
  const raw = JSON.parse(fs.readFileSync(samplePath, 'utf8'));
  const matchData = RecordLoader.load(raw);

  assert(matchData.game === expectedGame, `Expected sample game to be ${expectedGame}, got ${matchData.game}`);
  assert(Array.isArray(matchData.frames) && matchData.frames.length > 0, 'Expected sample to contain frames');

  const debugRenderer = RendererRegistry.create(matchData, 'debug');
  assert(debugRenderer, 'RendererRegistry.create(matchData, "debug") returned falsy');

  const sceneRenderer = RendererRegistry.create(matchData, 'retro_jrpg_scene');
  assert(sceneRenderer, 'RendererRegistry.create(matchData, "retro_jrpg_scene") returned falsy');

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
  const highlightTurns = new Set(matchData.frames.map((frame) => Number(frame.turnNumber)));
  entry.highlights.forEach((highlight) => {
    assert(
      Number.isInteger(highlight.turn) && highlightTurns.has(highlight.turn),
      `Expected highlight turn ${highlight.turn} to exist in ${entry.path}`
    );
    if (highlight.kind != null) {
      assert(validHighlightKinds.has(highlight.kind), `Invalid highlight kind ${highlight.kind} in ${entry.path}`);
    }
  });

  return {
    label: entry.label,
    game: matchData.game,
    schemaVersion: matchData.schemaVersion,
    frames,
  };
}

const fixedSample = manifest.matches.find((entry) => entry.path === 'matches/fixed-damage-01-flashlite-ao-collapse-vs-flash-ao.json');
const variableSample = manifest.matches.find((entry) => entry.path === 'matches/variable-damage-01-flashlite-rc-risk-vs-gpt5mini.json');

assert(fixedSample, 'Expected bundled FixedDamage sample in manifest');
assert(variableSample, 'Expected bundled VariableDamage sample in manifest');

const results = [
  runSampleSmoke(fixedSample, 'FixedDamageGame'),
  runSampleSmoke(variableSample, 'VariableDamageGame'),
];

console.log('viewer smoke-check OK', results);
