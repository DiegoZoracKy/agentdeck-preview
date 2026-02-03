// ============================================================================
// AgentDeck Replay Viewer App
// ============================================================================

let timeline = null;
let renderer = null;
let matchData = null;

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const viewerContainer = document.getElementById('viewer-container');
const controlsContainer = document.getElementById('controls-container');
const matchInfoContainer = document.getElementById('match-info');
const errorContainer = document.getElementById('error-container');

const btnPlay = document.getElementById('btn-play');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const btnReset = document.getElementById('btn-reset');
const speedSelect = document.getElementById('speed-select');
const progressBar = document.getElementById('progress-bar');
const progressFill = document.getElementById('progress-fill');
const statusText = document.getElementById('status-text');
const infoGrid = document.getElementById('info-grid');

// ============================================================================
// File Loading
// ============================================================================

function showError(message) {
  errorContainer.innerHTML = `<div class="error-message">Error: ${message}</div>`;
}

function clearError() {
  errorContainer.innerHTML = '';
}

async function loadMatchFile(file) {
  clearError();

  try {
    matchData = await RecordLoader.loadFromFile(file);
    initializeViewer(matchData);
  } catch (err) {
    showError(err.message);
    console.error('Load error:', err);
  }
}

function createRenderer(data) {
  if (typeof RendererRegistry === 'undefined') {
    throw new Error('Renderer registry not available.');
  }
  return RendererRegistry.create(data);
}

function initializeViewer(data) {
  // Hide drop zone, show viewer
  dropZone.style.display = 'none';
  viewerContainer.style.display = 'block';
  controlsContainer.style.display = 'flex';
  matchInfoContainer.style.display = 'block';

  // Create timeline
  timeline = new Timeline(data);

  // Create renderer
  renderer = createRenderer(data);
  renderer.init(viewerContainer, data);

  // Connect timeline to renderer
  timeline.onFrame((frame) => {
    renderer.renderFrame(frame);
    updateProgress();
  });

  timeline.onEnd((winner) => {
    renderer.renderVictory(winner, data.finalState, {
      outcome: data.outcome,
      forfeitReason: data.forfeitReason,
      forfeitingPlayer: data.forfeitingPlayer
    });
    btnPlay.textContent = 'Replay';
    updateStatus('Complete');

    // Reveal winner
    const winnerEl = document.querySelector('#info-winner .info-value');
    if (winnerEl && infoGrid.dataset.winner) {
      winnerEl.textContent = infoGrid.dataset.winner;
    }
  });

  timeline.onStateChange(() => {
    updateControls();
    updateProgress();
  });

  // Show match info
  displayMatchInfo(data);

  // Initial state - don't auto-play, just show "ready" state
  updateControls();
  updateProgress();
  updateStatus('Ready');
}

function resetViewer() {
  // Cleanup
  if (renderer) {
    renderer.destroy();
    renderer = null;
  }
  timeline = null;
  matchData = null;

  // Reset UI
  viewerContainer.style.display = 'none';
  viewerContainer.innerHTML = '';
  controlsContainer.style.display = 'none';
  matchInfoContainer.style.display = 'none';
  dropZone.style.display = 'block';

  clearError();
  updateStatus('Ready');
}

function displayMatchInfo(data) {
  const items = [
    { label: 'Match ID', value: data.matchId },
    { label: 'Game', value: data.game },
    { label: 'Players', value: data.players.join(' vs ') },
    { label: 'Winner', value: '<span class="winner-hidden">???</span>', id: 'winner' },
    { label: 'Turns', value: data.frames.length },
    { label: 'Seed', value: data.seed }
  ];

  infoGrid.innerHTML = items
    .map((item) => `
      <div class="info-item" ${item.id ? `id="info-${item.id}"` : ''}>
        <span class="info-label">${item.label}:</span>
        <span class="info-value">${item.value}</span>
      </div>
    `)
    .join('');

  // Store winner for reveal later
  infoGrid.dataset.winner = data.winner || 'Draw';
}

// ============================================================================
// Controls
// ============================================================================

function updateControls() {
  if (!timeline) return;

  if (timeline.isPlaying) {
    btnPlay.textContent = 'Pause';
  } else if (timeline.currentFrame >= timeline.totalFrames - 1) {
    btnPlay.textContent = 'Replay';
  } else {
    btnPlay.textContent = 'Play';
  }

  // Disable prev if at start (frame -1 or 0)
  btnPrev.disabled = timeline.currentFrame <= 0;
  // Disable next if at end
  btnNext.disabled = timeline.currentFrame >= timeline.totalFrames - 1;
}

function updateProgress() {
  if (!timeline || timeline.totalFrames === 0 || timeline.currentFrame < 0) {
    progressFill.style.width = '0%';
    return;
  }

  const progress = ((timeline.currentFrame + 1) / timeline.totalFrames) * 100;
  progressFill.style.width = `${progress}%`;
}

function updateStatus(text) {
  statusText.textContent = text;
}

// Button handlers
btnPlay.addEventListener('click', () => {
  if (!timeline) return;

  if (timeline.isPlaying) {
    timeline.pause();
    updateStatus('Paused');
  } else {
    timeline.play();
    updateStatus('Playing');
  }
});

btnPrev.addEventListener('click', () => {
  if (timeline) timeline.step(-1);
});

btnNext.addEventListener('click', () => {
  if (timeline) timeline.step(1);
});

btnReset.addEventListener('click', resetViewer);

speedSelect.addEventListener('change', (e) => {
  if (timeline) {
    timeline.setSpeed(parseFloat(e.target.value));
  }
});

// Progress bar click to seek
progressBar.addEventListener('click', (e) => {
  if (!timeline || timeline.totalFrames === 0) return;

  const rect = progressBar.getBoundingClientRect();
  const percent = (e.clientX - rect.left) / rect.width;
  const frameIndex = Math.floor(percent * timeline.totalFrames);
  timeline.seek(frameIndex);
});

// ============================================================================
// Drag & Drop
// ============================================================================

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');

  const file = e.dataTransfer.files[0];
  if (file && file.name.endsWith('.json')) {
    loadMatchFile(file);
  } else {
    showError('Please drop a JSON file');
  }
});

fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) {
    loadMatchFile(file);
  }
});

// ============================================================================
// Keyboard Controls
// ============================================================================

document.addEventListener('keydown', (e) => {
  // Don't capture when typing in inputs
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

  switch (e.code) {
    case 'Space':
      e.preventDefault();
      btnPlay.click();
      break;
    case 'ArrowLeft':
      e.preventDefault();
      if (timeline) timeline.step(-1);
      break;
    case 'ArrowRight':
      e.preventDefault();
      if (timeline) timeline.step(1);
      break;
    case 'Digit1':
      speedSelect.value = '0.5';
      if (timeline) timeline.setSpeed(0.5);
      break;
    case 'Digit2':
      speedSelect.value = '1';
      if (timeline) timeline.setSpeed(1);
      break;
    case 'Digit3':
      speedSelect.value = '2';
      if (timeline) timeline.setSpeed(2);
      break;
    case 'Digit4':
      speedSelect.value = '4';
      if (timeline) timeline.setSpeed(4);
      break;
    case 'KeyR':
      if (e.ctrlKey || e.metaKey) return; // Don't capture browser refresh
      resetViewer();
      break;
  }
});

// ============================================================================
// URL Parameter Support
// ============================================================================

async function loadFromUrl(url) {
  clearError();
  updateStatus('Loading');

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch: ${response.status}`);
    }
    const json = await response.json();
    matchData = RecordLoader.load(json);
    initializeViewer(matchData);
  } catch (err) {
    showError(`Failed to load from URL: ${err.message}`);
    console.error('URL load error:', err);
  }
}

// Check for ?match= URL parameter
const urlParams = new URLSearchParams(window.location.search);
const matchUrl = urlParams.get('match');
if (matchUrl) {
  loadFromUrl(matchUrl);
}
