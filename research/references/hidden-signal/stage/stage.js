/** Hidden Signal Stage: a Game-specific projection over Match Surface 0.2. */

function validateManifest(manifest) {
  if (!manifest || manifest.schema_version !== 1) throw new Error('Unsupported Stage manifest');
  if (manifest.epistemic_status !== 'one_run') throw new Error('Stage requires one_run status');
  if (!manifest.record_sha256 || !manifest.match_surface_sha256) {
    throw new Error('Stage manifest must identify Record and Match Surface');
  }
  return manifest;
}

function validateSurface(surface) {
  if (!surface || surface.schema_type !== 'match_surface' || surface.schema_version !== '0.2') {
    throw new Error('Hidden Signal Stage requires Match Surface 0.2');
  }
  if (surface.match?.game !== 'HiddenSignalGame') {
    throw new Error('Hidden Signal Stage received another Game');
  }
  if (!Array.isArray(surface.frames) || surface.frames.length === 0) {
    throw new Error('Hidden Signal Stage requires at least one frame');
  }
  return surface;
}

function buildReplay(surface) {
  validateSurface(surface);
  const first = surface.frames[0];
  return [
    {
      label: 'Start',
      action: null,
      player: first.player,
      state: first.state_before,
      phaseIndex: -1
    },
    ...surface.frames.map((frame) => ({
      label: `Turn ${frame.turn_context?.turn_number ?? frame.phase_index + 1}`,
      action: frame.action?.value ?? frame.action,
      player: frame.player,
      state: frame.state_after,
      phaseIndex: frame.phase_index
    }))
  ];
}

function displaySignal(state) {
  return state.revealed_signal || 'HIDDEN';
}

function frameProjection(step) {
  const state = step.state || {};
  const signal = displaySignal(state);
  return {
    label: step.label,
    action: step.action || 'Waiting',
    player: step.player,
    signal,
    concealed: signal === 'HIDDEN',
    inspectionCost: state.inspection_cost_total ?? 0,
    score: state.score ?? 0,
    choice: state.choice || 'No',
    correct: state.correct == null ? '—' : state.correct ? 'Yes' : 'No',
    done: Boolean(state.done)
  };
}

function renderStep(step, elements) {
  const view = frameProjection(step);
  elements.turnLabel.textContent = view.label;
  elements.actionLabel.textContent = view.action;
  elements.playerName.textContent = view.player;
  elements.signalValue.textContent = view.concealed ? '?' : view.signal;
  elements.signalCaption.textContent = view.concealed ? 'Signal concealed' : `Signal ${view.signal}`;
  elements.signalOrb.className = `signal-orb ${view.concealed ? 'is-hidden' : `is-${view.signal.toLowerCase()}`}`;
  elements.costValue.textContent = String(view.inspectionCost);
  elements.scoreValue.textContent = String(view.score);
  elements.choiceValue.textContent = view.choice;
  elements.correctValue.textContent = view.correct;
  elements.momentCopy.textContent =
    view.action === 'INSPECT'
      ? 'The Player paid one point to reveal the signal before committing.'
      : view.done
        ? `The Player committed to ${view.choice}. This exact Run is complete.`
        : 'The Player can inspect or commit without seeing the signal.';
  return view;
}

async function startStage(root = document) {
  const manifest = validateManifest(await fetch('canonical/manifest.json').then((item) => item.json()));
  const surface = validateSurface(
    await fetch(`canonical/${manifest.match_surface}`).then((item) => item.json())
  );
  const replay = buildReplay(surface);
  let index = 0;
  const elements = {
    epistemicLabel: root.querySelector('#epistemic-label'),
    matchId: root.querySelector('#match-id'),
    signalOrb: root.querySelector('#signal-orb'),
    signalValue: root.querySelector('#signal-value'),
    signalCaption: root.querySelector('#signal-caption'),
    turnLabel: root.querySelector('#turn-label'),
    actionLabel: root.querySelector('#action-label'),
    costValue: root.querySelector('#cost-value'),
    scoreValue: root.querySelector('#score-value'),
    choiceValue: root.querySelector('#choice-value'),
    correctValue: root.querySelector('#correct-value'),
    momentCopy: root.querySelector('#moment-copy'),
    steps: root.querySelector('#steps'),
    previous: root.querySelector('#previous'),
    next: root.querySelector('#next'),
    recordSha: root.querySelector('#record-sha'),
    surfaceSha: root.querySelector('#surface-sha'),
    sourcePointer: root.querySelector('#source-pointer'),
    playerName: root.querySelector('#player-name'),
    recordLink: root.querySelector('#record-link')
  };

  elements.epistemicLabel.textContent = manifest.label;
  elements.matchId.textContent = surface.match.match_id;
  elements.recordSha.textContent = `sha256:${manifest.record_sha256}`;
  elements.surfaceSha.textContent = `sha256:${manifest.match_surface_sha256}`;
  elements.sourcePointer.textContent = manifest.moment.source.action_pointer;
  elements.recordLink.href = `canonical/${manifest.record}`;

  const draw = () => {
    renderStep(replay[index], elements);
    elements.previous.disabled = index === 0;
    elements.next.disabled = index === replay.length - 1;
    elements.steps.textContent = `${index + 1} / ${replay.length}`;
  };
  elements.previous.addEventListener('click', () => {
    index = Math.max(0, index - 1);
    draw();
  });
  elements.next.addEventListener('click', () => {
    index = Math.min(replay.length - 1, index + 1);
    draw();
  });
  draw();
}

if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    startStage().catch((error) => {
      document.body.dataset.error = error.message;
      console.error(error);
    });
  });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    buildReplay,
    displaySignal,
    frameProjection,
    renderStep,
    validateManifest,
    validateSurface
  };
}
