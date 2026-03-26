#!/usr/bin/env node

const assert = require('assert');
const path = require('path');

const repoRoot = path.join(__dirname, '..', '..');
const RecordLoader = require(path.join(repoRoot, 'viewer/js/record-loader.js'));
const Timeline = require(path.join(repoRoot, 'viewer/js/timeline.js'));
const RendererRegistry = require(path.join(repoRoot, 'viewer/js/renderers/index.js'));

function makeRecord() {
  return {
    schema_version: '1.3',
    match_id: 'match-123',
    game: 'FixedDamageGame',
    players: ['Alice', 'Bob'],
    winner: 'Alice',
    seed: 42,
    final_state: {
      health: { Alice: 55, Bob: 0 },
      potions: { Alice: 1, Bob: 0 },
      turn: 2,
      last_action: { Alice: 'ATTACK', Bob: 'POTION' }
    },
    metadata: {
      match: {
        outcome: 'victory'
      }
    },
    events: [
      {
        type: 'unknown_event',
        data: { note: 'ignored' },
        context: {},
        timestamp: 1
      },
      {
        type: 'player_handshake_complete',
        data: {
          player: 'Alice',
          accepted: true,
          prompt_text: 'Handshake prompt',
          response_text: 'OK',
          normalized_response: 'OK'
        },
        context: {},
        timestamp: 2
      },
      {
        type: 'gameplay',
        data: {
          player: 'Bob',
          action: 'POTION',
          reasoning: 'Stay alive',
          state_before: {
            health: { Alice: 100, Bob: 20 },
            potions: { Alice: 3, Bob: 1 },
            turn: 2,
            last_action: {}
          },
          state_after: {
            health: { Alice: 100, Bob: 50 },
            potions: { Alice: 3, Bob: 0 },
            turn: 2,
            last_action: {}
          },
          turn_context: { turn_number: 2 },
          prompt: {
            prompt_text: 'Turn prompt 2',
            response_text: 'ACTION: POTION',
            duration: 11
          }
        },
        context: { phase_index: 1 },
        timestamp: 20
      },
      {
        type: 'gameplay',
        data: {
          player: 'Alice',
          action: 'ATTACK',
          reasoning: 'Go aggressive',
          state_before: {
            health: { Alice: 100, Bob: 100 },
            potions: { Alice: 3, Bob: 1 },
            turn: 1,
            last_action: {}
          },
          state_after: {
            health: { Alice: 100, Bob: 20 },
            potions: { Alice: 3, Bob: 1 },
            turn: 1,
            last_action: {}
          },
          turn_context: { turn_number: 1 },
          prompt: {
            prompt_text: 'Turn prompt 1',
            response_text: 'ACTION: ATTACK',
            duration: 10
          }
        },
        context: { turn_index: 0 },
        timestamp: 10
      },
      {
        type: 'player_conclusion',
        data: {
          player: 'Alice',
          reflection_text: 'That worked',
          outcome: 'victory',
          prompt_text: 'Reflect',
          response_text: 'That worked'
        },
        context: {},
        timestamp: 30
      }
    ]
  };
}

async function testRecordLoader() {
  const validationMissing = RecordLoader.validate({});
  assert.strictEqual(validationMissing.valid, false);
  assert(validationMissing.errors.includes('Missing required field: schema_version'));

  const validationOld = RecordLoader.validate({
    schema_version: '1.2',
    match_id: 'm',
    game: 'FixedDamageGame',
    players: [],
    events: []
  });
  assert.strictEqual(validationOld.valid, false);
  assert(validationOld.errors.some((e) => e.includes('Unsupported schema version: 1.2')));

  const record = makeRecord();
  const matchData = RecordLoader.load(record);
  const matchDataAgain = RecordLoader.load(record);

  assert.deepStrictEqual(matchData, matchDataAgain, 'RecordLoader.load() must be deterministic');
  assert.strictEqual(matchData.schemaVersion, '1.3');
  assert.strictEqual(matchData.frames.length, 2, 'Only gameplay events should become frames');
  assert.deepStrictEqual(
    matchData.frames.map((frame) => frame.index),
    [0, 1],
    'Frames should be ordered by turn_index/phase_index'
  );
  assert.strictEqual(matchData.frames[0].player, 'Alice');
  assert.strictEqual(matchData.frames[1].player, 'Bob');
  assert.deepStrictEqual(matchData.frames[0].stateBefore, {
    health: { Alice: 100, Bob: 100 },
    potions: { Alice: 3, Bob: 1 },
    turn: 1,
    lastAction: {}
  });
  assert.deepStrictEqual(matchData.lifecycle.handshakes, [
    {
      player: 'Alice',
      status: 'complete',
      accepted: true,
      promptText: 'Handshake prompt',
      responseText: 'OK',
      normalizedResponse: 'OK',
      reason: null,
      timestamp: 2
    }
  ]);
  assert.deepStrictEqual(matchData.lifecycle.conclusions, [
    {
      player: 'Alice',
      reflectionText: 'That worked',
      responseText: 'That worked',
      promptText: 'Reflect',
      timestamp: 30
    }
  ]);

  const sparse = RecordLoader.load({
    schema_version: '1.3',
    match_id: 'sparse',
    game: 'FixedDamageGame',
    players: ['Alice', 'Bob'],
    events: [
      {
        type: 'gameplay',
        data: {
          player: 'Alice',
          action: 'ATTACK',
          state_before: {},
          state_after: {}
        },
        context: {},
        timestamp: 1
      }
    ]
  });
  assert.strictEqual(sparse.winner, null);
  assert.strictEqual(sparse.outcome, 'draw');
  assert.strictEqual(sparse.forfeitReason, null);
  assert.strictEqual(sparse.forfeitingPlayer, null);
  assert.deepStrictEqual(sparse.frames[0].stateBefore, {
    health: {},
    potions: {},
    turn: 0,
    lastAction: {}
  });
  assert.strictEqual(sparse.frames[0].prompt, null);

  await assert.rejects(
    () =>
      RecordLoader.loadFromFile({
        async text() {
          return '{not json';
        }
      }),
    /Invalid JSON format/
  );
}

function testTimeline() {
  const matchData = RecordLoader.load(makeRecord());
  const timeline = new Timeline(matchData);
  const seenFrames = [];
  const endWinners = [];
  let stateChanges = 0;
  const capturedErrors = [];

  const originalConsoleError = console.error;
  console.error = (...args) => {
    capturedErrors.push(args.join(' '));
  };

  timeline.onFrame((frame) => {
    seenFrames.push(frame.index);
  });
  timeline.onFrame(() => {
    throw new Error('renderer failed');
  });
  timeline.onEnd((winner) => {
    endWinners.push(winner);
  });
  timeline.onStateChange(() => {
    stateChanges += 1;
  });

  timeline.step(1);
  assert.strictEqual(timeline.isPlaying, false);
  assert.strictEqual(timeline.currentFrame, 0);
  assert.deepStrictEqual(seenFrames, [0], 'step() should emit exactly one frame');
  assert.strictEqual(timeline.currentFrameData.player, 'Alice');

  timeline.seek(-99);
  assert.strictEqual(timeline.currentFrame, 0, 'seek() should clamp low values');

  timeline.seek(999);
  assert.strictEqual(timeline.currentFrame, 1, 'seek() should clamp high values');
  assert.deepStrictEqual(endWinners, ['Alice'], 'seek(last) should trigger onEnd when paused');

  const originalSetTimeout = global.setTimeout;
  const originalClearTimeout = global.clearTimeout;
  const scheduled = [];
  let nextTimerId = 1;

  global.setTimeout = (callback, delay) => {
    const token = { id: nextTimerId++, callback, delay, cancelled: false };
    scheduled.push(token);
    return token;
  };
  global.clearTimeout = (token) => {
    if (token) token.cancelled = true;
  };

  timeline.reset();
  timeline.setSpeed(2);
  timeline.play();
  assert.strictEqual(scheduled[0].delay, 500, 'play() should schedule baseDelay / speed');

  timeline.setSpeed(4);
  assert.strictEqual(scheduled[0].cancelled, true, 'speed changes should cancel the old timer');
  assert.strictEqual(scheduled[1].delay, 250, 'speed changes should reschedule at the new speed');

  for (const token of [...scheduled]) {
    if (!token.cancelled) token.callback();
  }
  while (scheduled.some((token) => !token.cancelled && token.id > 2)) {
    const pending = scheduled.filter((token) => !token.cancelled && token.id > 2);
    pending.forEach((token) => {
      token.cancelled = true;
      token.callback();
    });
  }

  global.setTimeout = originalSetTimeout;
  global.clearTimeout = originalClearTimeout;
  console.error = originalConsoleError;

  assert(seenFrames.includes(1), 'playback should advance through remaining frames');
  assert.strictEqual(
    seenFrames.filter((index) => index === 1).length >= 1,
    true,
    'end frame should be emitted'
  );
  assert(capturedErrors.some((msg) => msg.includes('Timeline: Frame callback error')));
  assert(stateChanges > 0, 'state change callbacks should fire during playback');
  assert.strictEqual(endWinners[endWinners.length - 1], 'Alice');
}

function testRendererRegistry() {
  const registry = RendererRegistry;
  registry._registry = {};

  class AlphaRenderer {}
  class ZetaRenderer {}

  registry.register('FixedDamageGame', 'zeta', ZetaRenderer);
  registry.register('FixedDamageGame', 'alpha', AlphaRenderer);

  assert.deepStrictEqual(registry.getAvailableSkins('FixedDamageGame'), ['alpha', 'zeta']);
  assert.strictEqual(registry.get('FixedDamageGame', 'alpha'), AlphaRenderer);
  assert.throws(
    () => registry.create({ game: 'UnknownGame' }, 'debug'),
    /No renderer registered/
  );

  const instance = registry.create({ game: 'FixedDamageGame' }, 'alpha');
  assert(instance instanceof AlphaRenderer);
}

async function main() {
  await testRecordLoader();
  testTimeline();
  testRendererRegistry();
  console.log('viewer contract tests OK');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
