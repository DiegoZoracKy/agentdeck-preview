;(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory()
  } else {
    root.MatchMetadataUtils = factory()
  }
})(typeof self !== 'undefined' ? self : this, function () {
  const MAX_HIGHLIGHT_LABEL = 50
  const HIGHLIGHT_KINDS = Object.freeze(['mistake', 'smart_move', 'surprise', 'turning_point'])
  const HIGHLIGHT_ICON_MAP = Object.freeze({
    mistake: '😬',
    smart_move: '💡',
    surprise: '🤯',
    turning_point: '⚡'
  })

  function normalizeString(value) {
    return typeof value === 'string' && value.trim() ? value.trim() : null
  }

  function normalizeHighlightKind(value) {
    const kind = normalizeString(value)
    return kind && HIGHLIGHT_KINDS.includes(kind) ? kind : null
  }

  function normalizeHighlight(entry) {
    if (!entry || typeof entry !== 'object') return null
    const turn = Number(entry.turn)
    const label = normalizeString(entry.label)
    const kind = normalizeHighlightKind(entry.kind)
    if (!Number.isInteger(turn) || turn < 1 || !label || label.length > MAX_HIGHLIGHT_LABEL) {
      return null
    }
    return { turn, label, ...(kind ? { kind } : {}) }
  }

  function normalizeSidecarMetadata(payload) {
    if (!payload || typeof payload !== 'object') return {}

    const subtitle = normalizeString(payload.subtitle)
    const synopsis = normalizeString(payload.synopsis)
    const highlights = Array.isArray(payload.highlights)
      ? payload.highlights.map(normalizeHighlight).filter(Boolean)
      : []

    const normalized = {}
    if (subtitle) normalized.subtitle = subtitle
    if (synopsis) normalized.synopsis = synopsis
    if (highlights.length) normalized.highlights = highlights
    return normalized
  }

  function mergeEntryWithMetadata(entry, payload) {
    const normalized = normalizeSidecarMetadata(payload)
    return {
      label: entry.label,
      path: entry.path,
      ...normalized
    }
  }

  function normalizeManifestEntries(payload) {
    const candidates = Array.isArray(payload && payload.matches) ? payload.matches : []
    return candidates
      .map((entry) => {
        if (!entry || typeof entry !== 'object') return null
        const path = normalizeString(entry.path)
        if (!path) return null
        const label = normalizeString(entry.label) || path.replace(/^matches\//, '')
        return mergeEntryWithMetadata({ label, path }, entry)
      })
      .filter(Boolean)
  }

  function resolveHighlightMarkers(frames, highlights) {
    if (!Array.isArray(frames) || !Array.isArray(highlights) || !frames.length || !highlights.length) {
      return []
    }

    const totalFrames = frames.length
    return highlights
      .map((highlight) => {
        const marker = normalizeHighlight(highlight)
        if (!marker) return null
        const frameIndex = frames.findIndex((frame) => Number(frame.turnNumber) === marker.turn)
        if (frameIndex < 0) return null
        return {
          turn: marker.turn,
          label: marker.label,
          ...(marker.kind ? { kind: marker.kind, icon: iconForHighlightKind(marker.kind) } : {}),
          frameIndex,
          percent: ((frameIndex + 1) / totalFrames) * 100
        }
      })
      .filter(Boolean)
  }

  function findActiveHighlight(markers, frame) {
    if (!Array.isArray(markers) || !frame) return null
    return markers.find((marker) => marker.turn === Number(frame.turnNumber)) || null
  }

  function iconForHighlightKind(kind) {
    return HIGHLIGHT_ICON_MAP[kind] || ''
  }

  return {
    MAX_HIGHLIGHT_LABEL,
    HIGHLIGHT_KINDS,
    HIGHLIGHT_ICON_MAP,
    normalizeHighlightKind,
    normalizeHighlight,
    normalizeSidecarMetadata,
    mergeEntryWithMetadata,
    normalizeManifestEntries,
    resolveHighlightMarkers,
    findActiveHighlight,
    iconForHighlightKind
  }
})
