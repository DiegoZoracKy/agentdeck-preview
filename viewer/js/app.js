// ============================================================================
// AgentDeck Replay Viewer App
// ============================================================================

let timeline = null
let renderer = null
let matchData = null
let currentSkin = null
let currentMatchSource = null
let preferredSkin = null
let currentMatchLabel = null
let frameCallback = null
let endCallback = null
let localMatchEntries = []

const DEFAULT_MATCH_PATH = 'matches/claude-sonnet-4.5-vs-gpt-4o-mini.json'
const STORAGE_MATCH_KEY = 'agentdeck.viewer.match'
const STORAGE_SKIN_KEY = 'agentdeck.viewer.skin'

// DOM Elements
const emptyState = document.getElementById('empty-state')
const btnEmptyUpload = document.getElementById('btn-empty-upload')
const btnUploadMatch = document.getElementById('btn-upload-match')
const btnLoadMatch = document.getElementById('btn-load-match')
const matchSelect = document.getElementById('match-select')
const mobileBtnMatch = document.getElementById('mobile-btn-match')
const mobileBtnSkin = document.getElementById('mobile-btn-skin')
const mobileBtnMore = document.getElementById('mobile-btn-more')
const mobileMatchLabel = document.getElementById('mobile-match-label')
const mobileSkinLabel = document.getElementById('mobile-skin-label')
const mobileSheet = document.getElementById('mobile-sheet')
const mobileSheetBackdrop = document.getElementById('mobile-sheet-backdrop')
const mobileSheetClose = document.getElementById('mobile-sheet-close')
const mobileSheetTitle = document.getElementById('mobile-sheet-title')
const mobileSheetMatch = document.getElementById('mobile-sheet-match')
const mobileSheetSkin = document.getElementById('mobile-sheet-skin')
const mobileSheetActions = document.getElementById('mobile-sheet-actions')
const mobileMatchSelect = document.getElementById('mobile-match-select')
const mobileLoadMatch = document.getElementById('mobile-load-match')
const mobileSkinSelect = document.getElementById('mobile-skin-select')
const mobileUploadMatch = document.getElementById('mobile-upload-match')
const fileInput = document.getElementById('file-input')
const viewerContainer = document.getElementById('viewer-container')
const controlsContainer = document.getElementById('controls-container')
const matchInfoContainer = document.getElementById('match-info')
const errorContainer = document.getElementById('error-container')

const btnPlay = document.getElementById('btn-play')
const btnPrev = document.getElementById('btn-prev')
const btnNext = document.getElementById('btn-next')
const speedSelect = document.getElementById('speed-select')
const skinSelect = document.getElementById('skin-select')
const progressBar = document.getElementById('progress-bar')
const progressFill = document.getElementById('progress-fill')
const statusText = document.getElementById('status-text')
const controlsTurn = document.getElementById('controls-turn')
const infoGrid = document.getElementById('info-grid')

// ============================================================================
// Storage + URL helpers
// ============================================================================

function readStorage(key) {
  try {
    return window.localStorage.getItem(key)
  } catch (err) {
    console.warn('Could not read localStorage key:', key, err)
    return null
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, value)
  } catch (err) {
    console.warn('Could not write localStorage key:', key, err)
  }
}

function removeStorage(key) {
  try {
    window.localStorage.removeItem(key)
  } catch (err) {
    console.warn('Could not remove localStorage key:', key, err)
  }
}

function syncUrlState() {
  const params = new URLSearchParams(window.location.search)

  if (currentMatchSource) params.set('match', currentMatchSource)
  else params.delete('match')

  if (currentSkin) params.set('skin', currentSkin)
  else params.delete('skin')

  const query = params.toString()
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}`
  window.history.replaceState({}, '', nextUrl)
}

function parseInitialPreferences() {
  const params = new URLSearchParams(window.location.search)
  const urlMatch = params.get('match')
  const urlSkin = params.get('skin')

  const storedMatch = readStorage(STORAGE_MATCH_KEY)
  const storedSkin = readStorage(STORAGE_SKIN_KEY)

  preferredSkin = urlSkin || storedSkin || null

  return {
    preferredMatch: urlMatch || storedMatch || null
  }
}

function setEmptyStateVisibility(visible) {
  emptyState.style.display = visible ? 'block' : 'none'
}

function isMobileLayout() {
  return window.matchMedia('(max-width: 700px)').matches
}

function shortenLabel(value, limit = 22) {
  const text = String(value || '').trim()
  if (!text) return '-'
  if (text.length <= limit) return text
  return `${text.slice(0, limit - 1)}…`
}

function prettySkinLabel(skin) {
  if (!skin) return '-'
  return skin.replace(/[-_]/g, ' ').toUpperCase()
}

function updateMobileCompactLabels() {
  if (!mobileMatchLabel || !mobileSkinLabel) return
  mobileMatchLabel.textContent = shortenLabel(currentMatchLabel || 'Custom')
  mobileSkinLabel.textContent = shortenLabel(prettySkinLabel(currentSkin), 14)
}

function setMatchOptionsOnSelect(selectEl) {
  if (!selectEl) return
  selectEl.innerHTML = localMatchEntries
    .map((entry) => `<option value="${entry.path}">${entry.label}</option>`)
    .join('')
}

function setSkinOptionsOnSelect(selectEl, skins) {
  if (!selectEl) return
  selectEl.innerHTML = skins
    .map((skin) => {
      const label = skin.replace(/[-_]/g, ' ').toUpperCase()
      return `<option value="${skin}">${label}</option>`
    })
    .join('')
}

function syncMatchSelectValue(path) {
  if (path && hasEntryForPath(path)) {
    if (matchSelect) matchSelect.value = path
    if (mobileMatchSelect) mobileMatchSelect.value = path
  }
}

function openMobileSheet(mode) {
  if (!mobileSheet) return

  const titles = {
    match: 'Load Match',
    skin: 'Load Skin',
    more: 'More'
  }
  mobileSheetTitle.textContent = titles[mode] || 'Controls'

  mobileSheetMatch.style.display = mode === 'match' ? 'flex' : 'none'
  mobileSheetSkin.style.display = mode === 'skin' ? 'flex' : 'none'
  mobileSheetActions.style.display = mode === 'more' ? 'flex' : 'none'

  mobileSheet.classList.add('open')
  mobileSheet.setAttribute('aria-hidden', 'false')
  document.body.classList.add('mobile-sheet-open')
}

function closeMobileSheet() {
  if (!mobileSheet) return
  mobileSheet.classList.remove('open')
  mobileSheet.setAttribute('aria-hidden', 'true')
  document.body.classList.remove('mobile-sheet-open')
}

// ============================================================================
// Loading + rendering
// ============================================================================

function showError(message) {
  errorContainer.innerHTML = `<div class="error-message">Error: ${message}</div>`
}

function clearError() {
  errorContainer.innerHTML = ''
}

function updateStatus(text) {
  statusText.textContent = text
  const headerStatusSupported = renderer && typeof renderer.setPlaybackStatus === 'function'
  controlsContainer.classList.toggle('status-in-header', Boolean(headerStatusSupported))
  if (headerStatusSupported) renderer.setPlaybackStatus(text)
}

function showViewerShell(visible) {
  viewerContainer.style.display = visible ? 'block' : 'none'
  controlsContainer.style.display = visible ? 'flex' : 'none'
  matchInfoContainer.style.display = visible ? 'block' : 'none'
}

function destroyViewerRuntime() {
  if (timeline) {
    if (frameCallback) timeline.offFrame(frameCallback)
    if (endCallback) timeline.offEnd(endCallback)
  }

  if (renderer) {
    renderer.destroy()
  }

  timeline = null
  renderer = null
  frameCallback = null
  endCallback = null
}

function createRenderer(data, skin) {
  if (typeof RendererRegistry === 'undefined') {
    throw new Error('Renderer registry not available.')
  }
  return RendererRegistry.create(data, skin)
}

function applySkinClass(skin) {
  const skinClasses = Array.from(controlsContainer.classList).filter((className) =>
    className.startsWith('skin-')
  )
  skinClasses.forEach((className) => controlsContainer.classList.remove(className))

  const normalized = String(skin || '').trim().replace(/_/g, '-')
  if (normalized) controlsContainer.classList.add(`skin-${normalized}`)
}

function persistSkinSelection(skin) {
  if (!skin) return
  writeStorage(STORAGE_SKIN_KEY, skin)
}

function setCurrentMatchSource(path) {
  currentMatchSource = path || null
  if (currentMatchSource) {
    writeStorage(STORAGE_MATCH_KEY, currentMatchSource)
    const localEntry = localMatchEntries.find((entry) => entry.path === currentMatchSource)
    currentMatchLabel = localEntry
      ? localEntry.label
      : (currentMatchSource.split('/').pop() || 'Match')
  } else {
    removeStorage(STORAGE_MATCH_KEY)
    currentMatchLabel = currentMatchLabel || 'Custom'
  }
  updateMobileCompactLabels()
}

function hasEntryForPath(path) {
  return localMatchEntries.some((entry) => entry.path === path)
}

function populateSkinSelector(data) {
  const skins = RendererRegistry.getAvailableSkins(data.game)

  if (!skins.length) {
    setSkinOptionsOnSelect(skinSelect, [])
    setSkinOptionsOnSelect(mobileSkinSelect, [])
    skinSelect.disabled = true
    if (mobileSkinSelect) mobileSkinSelect.disabled = true
    currentSkin = null
    updateMobileCompactLabels()
    return
  }

  skinSelect.disabled = false
  if (mobileSkinSelect) mobileSkinSelect.disabled = false
  setSkinOptionsOnSelect(skinSelect, skins)
  setSkinOptionsOnSelect(mobileSkinSelect, skins)

  const preferred = preferredSkin || currentSkin
  if (preferred && skins.includes(preferred)) currentSkin = preferred
  else currentSkin = skins.includes('ffvi_scene') ? 'ffvi_scene' : skins[0]

  skinSelect.value = currentSkin
  if (mobileSkinSelect) mobileSkinSelect.value = currentSkin
  persistSkinSelection(currentSkin)
  updateMobileCompactLabels()
}

function reconnectTimeline() {
  if (!timeline || !renderer) return

  if (frameCallback) timeline.offFrame(frameCallback)
  if (endCallback) timeline.offEnd(endCallback)

  frameCallback = (frame) => {
    renderer.renderFrame(frame)
    updateProgress()
    if (controlsTurn && matchData) {
      const total = matchData.frames.length
      const turn = frame.turnNumber || (frame.index + 1)
      controlsTurn.textContent = `Turn ${turn}/${total}`
    }
  }

  endCallback = (winner) => {
    renderer.renderVictory(winner, matchData.finalState, {
      outcome: matchData.outcome,
      forfeitReason: matchData.forfeitReason,
      forfeitingPlayer: matchData.forfeitingPlayer
    })
    btnPlay.textContent = 'Replay'
    updateStatus('Complete')

    const winnerEl = document.querySelector('#info-winner .info-value')
    if (winnerEl && infoGrid.dataset.winner) {
      winnerEl.textContent = infoGrid.dataset.winner
    }
  }

  timeline.onFrame(frameCallback)
  timeline.onEnd(endCallback)
}

function displayMatchInfo(data) {
  const players = data.players.join(' vs ')
  infoGrid.innerHTML = `
    <div class="match-table">
      <div class="match-table-grid">
        <div class="match-cell match-cell-game">
          <span class="match-label">Game</span>
          <span class="match-value" title="${data.game}">${data.game}</span>
        </div>
        <div class="match-cell match-cell-match-id">
          <span class="match-label">Match ID</span>
          <span class="match-value" title="${data.matchId}">${data.matchId}</span>
        </div>
        <div class="match-cell match-cell-seed">
          <span class="match-label">Seed</span>
          <span class="match-value">${data.seed}</span>
        </div>
        <div class="match-cell match-cell-turns">
          <span class="match-label">Turns</span>
          <span class="match-value">${data.frames.length}</span>
        </div>
      </div>
    </div>
    <div class="match-row match-row-bottom">
      <div class="info-item info-players">
        <span class="info-label">Players</span>
        <span class="info-value" title="${players}">${players}</span>
      </div>
      <div class="info-item info-winner" id="info-winner">
        <span class="info-label">Winner</span>
        <span class="info-value"><span class="winner-hidden">???</span></span>
      </div>
    </div>
  `

  infoGrid.dataset.winner = data.winner || 'Draw'
}

function initializeViewer(data) {
  destroyViewerRuntime()
  matchData = data

  showViewerShell(true)
  setEmptyStateVisibility(false)

  populateSkinSelector(data)
  applySkinClass(currentSkin)

  timeline = new Timeline(data)
  renderer = createRenderer(data, currentSkin)
  renderer.init(viewerContainer, data)

  reconnectTimeline()

  timeline.onStateChange(() => {
    updateControls()
    updateProgress()
  })

  if (controlsTurn) {
    const first = data.frames[0]
    const turn = first ? (first.turnNumber || 1) : 1
    controlsTurn.textContent = `Turn ${turn}/${data.frames.length}`
  }

  displayMatchInfo(data)
  updateControls()
  updateProgress()
  updateStatus('Ready')
}

async function loadFromUrl(url, options = {}) {
  const { persistMatch = true, showEmptyOnFailure = true } = options
  const previousStatus = statusText.textContent || 'Ready'

  clearError()
  updateStatus('Loading')

  try {
    const response = await fetch(url, { cache: 'no-store' })
    if (!response.ok) throw new Error(`Failed to fetch: ${response.status}`)

    const json = await response.json()
    initializeViewer(RecordLoader.load(json))
    setCurrentMatchSource(url)
    if (!persistMatch) removeStorage(STORAGE_MATCH_KEY)
    syncMatchSelectValue(url)
    syncUrlState()
    closeMobileSheet()
    return true
  } catch (err) {
    showError(`Failed to load match: ${err.message}`)
    console.error('Match load error:', err)
    updateStatus(previousStatus)
    if (showEmptyOnFailure && !matchData) {
      showViewerShell(false)
      setEmptyStateVisibility(true)
    }
    return false
  }
}

async function loadMatchFile(file) {
  const previousStatus = statusText.textContent || 'Ready'
  clearError()
  updateStatus('Loading')

  try {
    initializeViewer(await RecordLoader.loadFromFile(file))
    currentMatchLabel = file.name || 'Uploaded JSON'
    setCurrentMatchSource(null)
    syncUrlState()
    closeMobileSheet()
  } catch (err) {
    showError(err.message)
    console.error('Load error:', err)
    updateStatus(previousStatus)
  }
}

function switchSkin(newSkin) {
  if (!matchData || !timeline || newSkin === currentSkin) return

  const wasPlaying = timeline.isPlaying
  const currentFrame = timeline.currentFrame

  if (wasPlaying) timeline.pause()
  if (renderer) renderer.destroy()

  currentSkin = newSkin
  preferredSkin = newSkin
  persistSkinSelection(currentSkin)
  applySkinClass(currentSkin)
  if (skinSelect) skinSelect.value = currentSkin
  if (mobileSkinSelect) mobileSkinSelect.value = currentSkin
  updateMobileCompactLabels()
  renderer = createRenderer(matchData, currentSkin)
  renderer.init(viewerContainer, matchData)

  if (currentFrame >= 0 && currentFrame < matchData.frames.length) {
    renderer.renderFrame(matchData.frames[currentFrame])
  }

  reconnectTimeline()
  syncUrlState()

  if (wasPlaying) timeline.play()
}

function normalizeManifestEntries(payload) {
  const candidates = Array.isArray(payload?.matches) ? payload.matches : []
  return candidates
    .map((entry) => {
      if (!entry || typeof entry !== 'object') return null
      const path = typeof entry.path === 'string' ? entry.path.trim() : ''
      if (!path) return null
      const label = typeof entry.label === 'string' && entry.label.trim()
        ? entry.label.trim()
        : path.replace(/^matches\//, '')
      return { label, path }
    })
    .filter(Boolean)
}

function renderLocalMatchOptions() {
  setMatchOptionsOnSelect(matchSelect)
  setMatchOptionsOnSelect(mobileMatchSelect)

  const hasEntries = localMatchEntries.length > 0
  if (matchSelect) matchSelect.disabled = !hasEntries
  if (mobileMatchSelect) mobileMatchSelect.disabled = !hasEntries
  if (btnLoadMatch) btnLoadMatch.disabled = !hasEntries
  if (mobileLoadMatch) mobileLoadMatch.disabled = !hasEntries

  if (!currentMatchLabel && hasEntries) {
    currentMatchLabel = localMatchEntries[0].label
  }
  updateMobileCompactLabels()
}

async function loadLocalMatchManifest() {
  try {
    const response = await fetch('matches/manifest.json', { cache: 'no-store' })
    if (!response.ok) {
      localMatchEntries = []
      renderLocalMatchOptions()
      return
    }

    localMatchEntries = normalizeManifestEntries(await response.json())
    renderLocalMatchOptions()
  } catch (err) {
    localMatchEntries = []
    renderLocalMatchOptions()
    console.warn('Local match manifest not available:', err)
  }
}

// ============================================================================
// Playback controls
// ============================================================================

function updateControls() {
  if (!timeline) return

  if (timeline.isPlaying) btnPlay.textContent = 'Pause'
  else if (timeline.currentFrame >= timeline.totalFrames - 1) btnPlay.textContent = 'Replay'
  else btnPlay.textContent = 'Play'

  btnPrev.disabled = timeline.currentFrame <= 0
  btnNext.disabled = timeline.currentFrame >= timeline.totalFrames - 1
}

function updateProgress() {
  if (!timeline || timeline.totalFrames === 0 || timeline.currentFrame < 0) {
    progressFill.style.width = '0%'
    return
  }

  const progress = ((timeline.currentFrame + 1) / timeline.totalFrames) * 100
  progressFill.style.width = `${progress}%`
}

btnPlay.addEventListener('click', () => {
  if (!timeline) return

  if (timeline.isPlaying) {
    timeline.pause()
    updateStatus('Paused')
  } else {
    timeline.play()
    updateStatus('Playing')
  }
})

btnPrev.addEventListener('click', () => {
  if (timeline) timeline.step(-1)
})

btnNext.addEventListener('click', () => {
  if (timeline) timeline.step(1)
})

speedSelect.addEventListener('change', (e) => {
  if (timeline) timeline.setSpeed(parseFloat(e.target.value))
})

skinSelect.addEventListener('change', (e) => {
  switchSkin(e.target.value)
})

btnLoadMatch.addEventListener('click', () => {
  if (!matchSelect.value) return
  loadFromUrl(matchSelect.value)
})

btnUploadMatch.addEventListener('click', () => fileInput.click())
if (btnEmptyUpload) btnEmptyUpload.addEventListener('click', () => fileInput.click())
if (mobileUploadMatch) mobileUploadMatch.addEventListener('click', () => fileInput.click())

if (mobileBtnMatch) {
  mobileBtnMatch.addEventListener('click', () => {
    syncMatchSelectValue(currentMatchSource || matchSelect.value)
    openMobileSheet('match')
  })
}

if (mobileBtnSkin) {
  mobileBtnSkin.addEventListener('click', () => {
    if (mobileSkinSelect && currentSkin) mobileSkinSelect.value = currentSkin
    openMobileSheet('skin')
  })
}

if (mobileBtnMore) {
  mobileBtnMore.addEventListener('click', () => {
    openMobileSheet('more')
  })
}

if (mobileSheetClose) mobileSheetClose.addEventListener('click', closeMobileSheet)
if (mobileSheetBackdrop) mobileSheetBackdrop.addEventListener('click', closeMobileSheet)

if (mobileLoadMatch) {
  mobileLoadMatch.addEventListener('click', () => {
    if (!mobileMatchSelect || !mobileMatchSelect.value) return
    loadFromUrl(mobileMatchSelect.value)
  })
}

if (mobileSkinSelect) {
  mobileSkinSelect.addEventListener('change', (e) => {
    switchSkin(e.target.value)
    if (isMobileLayout()) closeMobileSheet()
  })
}

if (matchSelect && mobileMatchSelect) {
  matchSelect.addEventListener('change', () => {
    mobileMatchSelect.value = matchSelect.value
  })
  mobileMatchSelect.addEventListener('change', () => {
    matchSelect.value = mobileMatchSelect.value
  })
}

fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0]
  if (file) loadMatchFile(file)
  fileInput.value = ''
})

progressBar.addEventListener('click', (e) => {
  if (!timeline || timeline.totalFrames === 0) return

  const rect = progressBar.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  const frameIndex = Math.floor(percent * timeline.totalFrames)
  timeline.seek(frameIndex)
})

// ============================================================================
// Keyboard controls
// ============================================================================

document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return

  switch (e.code) {
    case 'Space':
      e.preventDefault()
      btnPlay.click()
      break
    case 'ArrowLeft':
      e.preventDefault()
      if (timeline) timeline.step(-1)
      break
    case 'ArrowRight':
      e.preventDefault()
      if (timeline) timeline.step(1)
      break
    case 'Digit1':
      speedSelect.value = '0.5'
      if (timeline) timeline.setSpeed(0.5)
      break
    case 'Digit2':
      speedSelect.value = '1'
      if (timeline) timeline.setSpeed(1)
      break
    case 'Digit3':
      speedSelect.value = '2'
      if (timeline) timeline.setSpeed(2)
      break
    case 'Digit4':
      speedSelect.value = '4'
      if (timeline) timeline.setSpeed(4)
      break
    case 'Escape':
      closeMobileSheet()
      break
  }
})

window.addEventListener('resize', () => {
  if (!isMobileLayout()) closeMobileSheet()
})

// ============================================================================
// App init
// ============================================================================

async function initApp() {
  showViewerShell(false)
  setEmptyStateVisibility(false)
  updateStatus('Loading')
  skinSelect.disabled = true

  const { preferredMatch } = parseInitialPreferences()
  await loadLocalMatchManifest()

  const manifestDefault = localMatchEntries[0]?.path || null
  const startupMatch = preferredMatch || manifestDefault || DEFAULT_MATCH_PATH
  const startupEntry = localMatchEntries.find((entry) => entry.path === startupMatch)
  currentMatchLabel = startupEntry ? startupEntry.label : (startupMatch.split('/').pop() || 'Match')
  updateMobileCompactLabels()

  if (hasEntryForPath(startupMatch)) syncMatchSelectValue(startupMatch)

  const loaded = await loadFromUrl(startupMatch, { persistMatch: true, showEmptyOnFailure: true })

  if (!loaded) {
    updateStatus('Ready')
    if (!localMatchEntries.length) {
      showError('No local matches available. Upload a JSON file to begin.')
    }
  }
}

initApp()
