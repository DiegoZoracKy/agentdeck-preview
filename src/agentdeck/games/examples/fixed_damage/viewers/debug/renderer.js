/**
 * CombatDebugRenderer - State-focused combat renderer for debugging.
 *
 * Per SPEC-VIEWER §5.3:
 * - R1: init() MUST be callable multiple times (re-init for new match)
 * - R2: renderFrame() MUST handle any valid GameplayFrame
 * - R3: destroy() MUST remove all DOM elements added by renderer
 * - R4: Renderers MUST NOT modify MatchData or GameplayFrame objects
 */

class CombatDebugRenderer {
  constructor() {
    this._container = null;
    this._matchData = null;
    this._elements = {};
  }

  /**
   * Initialize renderer in container
   * @param {HTMLElement} container
   * @param {MatchData} matchData
   */
  init(container, matchData) {
    // R1: Clean up previous init
    this.destroy();

    this._container = container;
    this._matchData = matchData;

    this._createDebugView();
    this._renderLifecyclePanels();
  }

  /**
   * Render a gameplay frame
   * @param {GameplayFrame} frame
   */
  renderFrame(frame) {
    if (!this._container) return;

    // Update frame info
    this._elements.frameNumber.textContent = frame.index + 1;
    this._elements.turnNumber.textContent = frame.turnNumber;
    this._elements.player.textContent = frame.player;
    this._elements.action.textContent = frame.action;

    // Update state before/after
    this._elements.stateBefore.textContent = JSON.stringify(frame.stateBefore, null, 2);
    this._elements.stateAfter.textContent = JSON.stringify(frame.stateAfter, null, 2);

    // Update reasoning if present
    if (frame.reasoning) {
      this._elements.reasoning.textContent = frame.reasoning;
      this._elements.reasoningContainer.style.display = 'block';
    } else {
      this._elements.reasoningContainer.style.display = 'none';
    }

    // Update prompt data if present
    if (frame.prompt) {
      this._elements.promptText.textContent = frame.prompt.promptText || 'N/A';
      this._elements.responseText.textContent = frame.prompt.responseText || 'N/A';
      this._elements.duration.textContent = `${frame.prompt.duration || 0}ms`;
      this._elements.promptContainer.style.display = 'block';
    } else {
      this._elements.promptContainer.style.display = 'none';
    }
  }

  /**
   * Render victory screen
   * @param {string | null} winner
   * @param {GameState} finalState
   */
  renderVictory(winner, finalState, outcomeInfo = {}) {
    if (!this._container) return;

    const { outcome, forfeitReason, forfeitingPlayer } = outcomeInfo;

    this._elements.victoryContainer.style.display = 'block';
    this._elements.victoryTitle.textContent = outcome === 'forfeit' ? 'Match Forfeited' : 'Match Complete';
    this._elements.winner.textContent = winner || 'Draw';
    this._elements.finalState.textContent = JSON.stringify(finalState, null, 2);

    if (outcome === 'forfeit') {
      this._elements.outcomeRow.style.display = 'flex';
      this._elements.outcome.textContent = 'Forfeit';
      this._elements.outcomeDetailRow.style.display = 'flex';
      this._elements.outcomeDetail.textContent = forfeitingPlayer
        ? `${forfeitingPlayer} ${this._formatForfeitReason(forfeitReason)}`
        : this._formatForfeitReason(forfeitReason);
      return;
    }

    this._elements.outcomeRow.style.display = 'none';
    this._elements.outcome.textContent = '';
    this._elements.outcomeDetailRow.style.display = 'none';
    this._elements.outcomeDetail.textContent = '';
  }

  /**
   * Cleanup resources
   */
  destroy() {
    if (this._container && this._elements.root) {
      this._container.removeChild(this._elements.root);
    }
    this._container = null;
    this._matchData = null;
    this._elements = {};
  }

  // =========================================================================
  // Private: View Creation
  // =========================================================================

  _createDebugView() {
    const root = document.createElement('div');
    root.className = 'debug-viewer';

    root.innerHTML = `
      <div class="debug-header">
        <h2>Debug Viewer - ${this._escapeHtml(this._matchData.game)}</h2>
        <div class="debug-match-info">
          <span>Match: ${this._escapeHtml(this._matchData.matchId)}</span>
          <span>Players: ${this._matchData.players.map(p => this._escapeHtml(p)).join(' vs ')}</span>
        </div>
      </div>

      <div id="debug-handshake-container" class="debug-section" style="display: none;">
        <h3>Handshake Prompts</h3>
        <div id="debug-handshake-list" class="debug-lifecycle-list"></div>
      </div>

      <div class="debug-frame-info">
        <div class="debug-row">
          <label>Frame:</label>
          <span id="debug-frame-number">-</span>
        </div>
        <div class="debug-row">
          <label>Turn:</label>
          <span id="debug-turn-number">-</span>
        </div>
        <div class="debug-row">
          <label>Player:</label>
          <span id="debug-player">-</span>
        </div>
        <div class="debug-row">
          <label>Action:</label>
          <span id="debug-action">-</span>
        </div>
        <div id="debug-highlight-row" class="debug-highlight-row" style="display: none;">
          <span id="debug-highlight-icon" class="debug-highlight-icon"></span>
          <span id="debug-highlight-text" class="debug-highlight-text"></span>
        </div>
      </div>

      <div class="debug-state-comparison">
        <div class="debug-state-column">
          <h3>State Before</h3>
          <pre id="debug-state-before">{}</pre>
        </div>
        <div class="debug-state-column">
          <h3>State After</h3>
          <pre id="debug-state-after">{}</pre>
        </div>
      </div>

      <div id="debug-reasoning-container" class="debug-section" style="display: none;">
        <h3>Model-reported reasoning</h3>
        <pre id="debug-reasoning"></pre>
      </div>

      <div id="debug-prompt-container" class="debug-section" style="display: none;">
        <h3>Prompt/Response</h3>
        <div class="debug-prompt-response">
          <div class="debug-prompt-section">
            <h4>Prompt</h4>
            <pre id="debug-prompt-text"></pre>
          </div>
          <div class="debug-prompt-section">
            <h4>Response</h4>
            <pre id="debug-response-text"></pre>
          </div>
          <div class="debug-row">
            <label>Duration:</label>
            <span id="debug-duration">-</span>
          </div>
        </div>
      </div>

      <div id="debug-victory-container" class="debug-victory" style="display: none;">
        <h2 id="debug-victory-title">Match Complete</h2>
        <div id="debug-outcome-row" class="debug-row" style="display: none;">
          <label>Outcome:</label>
          <span id="debug-outcome"></span>
        </div>
        <div id="debug-outcome-detail-row" class="debug-row" style="display: none;">
          <label>Detail:</label>
          <span id="debug-outcome-detail"></span>
        </div>
        <div class="debug-row">
          <label>Winner:</label>
          <span id="debug-winner">-</span>
        </div>
        <h3>Final State</h3>
        <pre id="debug-final-state">{}</pre>
      </div>

      <div id="debug-conclusion-container" class="debug-section" style="display: none;">
        <h3>Conclusions / Reflections</h3>
        <div id="debug-conclusion-list" class="debug-lifecycle-list"></div>
      </div>
    `;

    // Store element references
    this._elements.root = root;
    this._elements.handshakeContainer = root.querySelector('#debug-handshake-container');
    this._elements.handshakeList = root.querySelector('#debug-handshake-list');
    this._elements.conclusionContainer = root.querySelector('#debug-conclusion-container');
    this._elements.conclusionList = root.querySelector('#debug-conclusion-list');
    this._elements.frameNumber = root.querySelector('#debug-frame-number');
    this._elements.turnNumber = root.querySelector('#debug-turn-number');
    this._elements.player = root.querySelector('#debug-player');
    this._elements.action = root.querySelector('#debug-action');
    this._elements.highlightRow = root.querySelector('#debug-highlight-row');
    this._elements.highlightIcon = root.querySelector('#debug-highlight-icon');
    this._elements.highlightText = root.querySelector('#debug-highlight-text');
    this._elements.stateBefore = root.querySelector('#debug-state-before');
    this._elements.stateAfter = root.querySelector('#debug-state-after');
    this._elements.reasoningContainer = root.querySelector('#debug-reasoning-container');
    this._elements.reasoning = root.querySelector('#debug-reasoning');
    this._elements.promptContainer = root.querySelector('#debug-prompt-container');
    this._elements.promptText = root.querySelector('#debug-prompt-text');
    this._elements.responseText = root.querySelector('#debug-response-text');
    this._elements.duration = root.querySelector('#debug-duration');
    this._elements.victoryContainer = root.querySelector('#debug-victory-container');
    this._elements.victoryTitle = root.querySelector('#debug-victory-title');
    this._elements.outcomeRow = root.querySelector('#debug-outcome-row');
    this._elements.outcome = root.querySelector('#debug-outcome');
    this._elements.outcomeDetailRow = root.querySelector('#debug-outcome-detail-row');
    this._elements.outcomeDetail = root.querySelector('#debug-outcome-detail');
    this._elements.winner = root.querySelector('#debug-winner');
    this._elements.finalState = root.querySelector('#debug-final-state');

    this._container.appendChild(root);
  }

  _renderLifecyclePanels() {
    const lifecycle = this._matchData?.lifecycle || {};
    const handshakes = Array.isArray(lifecycle.handshakes) ? lifecycle.handshakes : [];
    const conclusions = Array.isArray(lifecycle.conclusions) ? lifecycle.conclusions : [];

    if (handshakes.length > 0) {
      this._elements.handshakeContainer.style.display = 'block';
      this._elements.handshakeList.innerHTML = handshakes
        .map((entry) => {
          const status = this._formatHandshakeStatus(entry);
          const prompt = entry.promptText || 'N/A';
          const response = entry.responseText || entry.normalizedResponse || 'N/A';
          return `
            <details class="debug-lifecycle-item">
              <summary>
                <span class="debug-lifecycle-player">${this._escapeHtml(entry.player)}</span>
                <span class="debug-lifecycle-status">${this._escapeHtml(status)}</span>
              </summary>
              <div class="debug-lifecycle-body">
                <div class="debug-lifecycle-grid">
                  <div class="debug-lifecycle-block">
                    <h4>Prompt</h4>
                    <pre>${this._escapeHtml(prompt)}</pre>
                  </div>
                  <div class="debug-lifecycle-block">
                    <h4>Response</h4>
                    <pre>${this._escapeHtml(response)}</pre>
                  </div>
                </div>
              </div>
            </details>
          `;
        })
        .join('');
    } else {
      this._elements.handshakeContainer.style.display = 'none';
    }

    if (conclusions.length > 0) {
      this._elements.conclusionContainer.style.display = 'block';
      this._elements.conclusionList.innerHTML = conclusions
        .map((entry) => {
          const prompt = entry.promptText || 'N/A';
          const reflection = entry.reflectionText || entry.responseText || 'N/A';
          return `
            <details class="debug-lifecycle-item">
              <summary>
                <span class="debug-lifecycle-player">${this._escapeHtml(entry.player)}</span>
                <span class="debug-lifecycle-status">Conclusion</span>
              </summary>
              <div class="debug-lifecycle-body">
                <div class="debug-lifecycle-grid">
                  <div class="debug-lifecycle-block">
                    <h4>Prompt</h4>
                    <pre>${this._escapeHtml(prompt)}</pre>
                  </div>
                  <div class="debug-lifecycle-block">
                    <h4>Reflection</h4>
                    <pre>${this._escapeHtml(reflection)}</pre>
                  </div>
                </div>
              </div>
            </details>
          `;
        })
        .join('');
    } else {
      this._elements.conclusionContainer.style.display = 'none';
    }
  }

  _formatHandshakeStatus(entry) {
    if (entry.status === 'aborted') {
      return `Aborted${entry.reason ? ` (${entry.reason})` : ''}`;
    }
    if (entry.status === 'complete') {
      return entry.accepted === false ? 'Rejected' : 'Accepted';
    }
    return 'Started';
  }

  _escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  _formatForfeitReason(reason) {
    switch (reason) {
      case 'parse_failure':
        return 'failed to provide a valid action';
      case 'timeout':
        return 'ran out of time';
      case 'invalid_action':
        return 'chose an invalid action';
      case 'disconnect':
        return 'disconnected';
      default:
        return 'forfeited the match';
    }
  }

  setActiveHighlight(highlight) {
    const row = this._elements.highlightRow;
    const icon = this._elements.highlightIcon;
    const text = this._elements.highlightText;
    if (!row || !icon || !text) return;

    if (!highlight || !highlight.label) {
      row.style.display = 'none';
      row.removeAttribute('data-kind');
      icon.textContent = '';
      text.textContent = '';
      return;
    }

    row.style.display = 'flex';
    if (highlight.kind) row.dataset.kind = highlight.kind;
    else row.removeAttribute('data-kind');
    icon.textContent = highlight.icon || '';
    text.textContent = highlight.label;
  }
}

// Register renderer for the bundled combat games (if registry present).
if (typeof RendererRegistry !== 'undefined') {
  RendererRegistry.register('ArchivistChoiceGame', 'debug', CombatDebugRenderer);
  RendererRegistry.register('FixedDamageGame', 'debug', CombatDebugRenderer);
  RendererRegistry.register('VariableDamageGame', 'debug', CombatDebugRenderer);
}

// Export for module systems, also available as global
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CombatDebugRenderer;
}
