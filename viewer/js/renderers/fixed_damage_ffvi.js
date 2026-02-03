/**
 * FixedDamageFFVIRenderer - Final Fantasy VI style battle renderer
 *
 * Per SPEC-VIEWER §5.3:
 * - R1: init() MUST be callable multiple times (re-init for new match)
 * - R2: renderFrame() MUST handle any valid GameplayFrame
 * - R3: destroy() MUST remove all DOM elements added by renderer
 * - R4: Renderers MUST NOT modify MatchData or GameplayFrame objects
 */

class FixedDamageFFVIRenderer {
  constructor() {
    this._container = null;
    this._matchData = null;
    this._elements = {};
    this._animationQueue = [];
    this._isAnimating = false;
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
    this._maxHealth = this._resolveMaxHealth();

    this._createBattleScene();
    this._renderInitialState();
  }

  /**
   * Render a gameplay frame
   * @param {GameplayFrame} frame
   */
  renderFrame(frame) {
    if (!this._container) return;

    // Clear victory overlay if present (for replay)
    this._clearVictoryOverlay();

    // Update HP bars
    this._updateHealthBars(frame.stateAfter);

    // Update potion counts
    this._updatePotions(frame.stateAfter);

    // Show action animation
    this._showAction(frame.player, frame.action, frame);

    // Update turn indicator
    this._updateTurnIndicator(frame.turnNumber, frame.index + 1);

    // Update narration
    this._updateNarration(frame);
  }

  /**
   * Render victory screen
   * @param {string | null} winner
   * @param {GameState} finalState
   * @param {object} outcomeInfo - Optional outcome details
   */
  renderVictory(winner, finalState, outcomeInfo = {}) {
    if (!this._container) return;

    const overlay = document.createElement('div');
    overlay.className = 'ffvi-victory-overlay';

    const { outcome, forfeitReason, forfeitingPlayer } = outcomeInfo;

    if (winner) {
      // Check if it was a forfeit
      if (outcome === 'forfeit' && forfeitingPlayer) {
        const reasonText = this._formatForfeitReason(forfeitReason);
        overlay.innerHTML = `
          <div class="ffvi-victory-content">
            <div class="ffvi-victory-text ffvi-forfeit">FORFEIT!</div>
            <div class="ffvi-winner-name">${this._escapeHtml(winner)} wins</div>
            <div class="ffvi-victory-stats">
              ${this._escapeHtml(forfeitingPlayer)} ${reasonText}
            </div>
          </div>
        `;

      } else {
        overlay.innerHTML = `
          <div class="ffvi-victory-content">
            <div class="ffvi-victory-text">VICTORY!</div>
            <div class="ffvi-winner-name">${this._escapeHtml(winner)}</div>
            <div class="ffvi-victory-stats">
              Final HP: ${finalState.health[winner] || 0}
            </div>
          </div>
        `;
      }
    } else {
      overlay.innerHTML = `
        <div class="ffvi-victory-content">
          <div class="ffvi-victory-text ffvi-draw">DRAW</div>
          <div class="ffvi-victory-stats">
            Both combatants fell!
          </div>
        </div>
      `;
    }

    this._elements.battleScene.appendChild(overlay);

    // Trigger animation
    requestAnimationFrame(() => {
      overlay.classList.add('visible');
    });
  }

  /**
   * Format forfeit reason for display
   * @private
   */
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

  /**
   * Clear victory overlay (for replay)
   */
  _clearVictoryOverlay() {
    if (!this._elements.battleScene) return;
    const overlay = this._elements.battleScene.querySelector('.ffvi-victory-overlay');
    if (overlay) {
      overlay.remove();
    }
    // Also clear defeated state from player panels
    const panels = this._elements.battleScene.querySelectorAll('.ffvi-player-panel');
    panels.forEach(panel => panel.classList.remove('ffvi-defeated'));
  }

  /**
   * Cleanup resources
   */
  destroy() {
    if (this._container && this._elements.battleScene) {
      this._container.removeChild(this._elements.battleScene);
    }
    this._container = null;
    this._matchData = null;
    this._elements = {};
  }

  // =========================================================================
  // Private: Scene Creation
  // =========================================================================

  _createBattleScene() {
    const scene = document.createElement('div');
    scene.className = 'ffvi-battle-scene';

    // Title bar
    const titleBar = document.createElement('div');
    titleBar.className = 'ffvi-title-bar';
    titleBar.textContent = this._matchData.game.replace(/Game$/, '') + ' BATTLE';
    scene.appendChild(titleBar);

    // Battle area
    const battleArea = document.createElement('div');
    battleArea.className = 'ffvi-battle-area';

    // Create player panels
    const players = this._matchData.players;
    const player1Panel = this._createPlayerPanel(players[0], 'left');
    const player2Panel = this._createPlayerPanel(players[1] || 'CPU', 'right');

    // Action display (center)
    const actionDisplay = document.createElement('div');
    actionDisplay.className = 'ffvi-action-display';
    this._elements.actionDisplay = actionDisplay;

    battleArea.appendChild(player1Panel);
    battleArea.appendChild(actionDisplay);
    battleArea.appendChild(player2Panel);
    scene.appendChild(battleArea);

    // Narration box
    const narrationBox = document.createElement('div');
    narrationBox.className = 'ffvi-narration-box';
    const p1 = this._matchData.players[0];
    const p2 = this._matchData.players[1] || 'CPU';
    narrationBox.innerHTML = `
      <div class="ffvi-narration-text">${this._escapeHtml(p1)} vs ${this._escapeHtml(p2)} — Press Play to begin!</div>
      <div class="ffvi-reasoning-container" style="display: none;">
        <div class="ffvi-reasoning-toggle expanded" onclick="this.classList.toggle('expanded'); this.nextElementSibling.classList.toggle('visible'); this.querySelector('span:last-child').textContent = this.classList.contains('expanded') ? 'Hide Reasoning' : 'Show Reasoning';">
          <span class="arrow">▶</span> <span>Hide Reasoning</span>
        </div>
        <div class="ffvi-reasoning-content visible">
          <div class="ffvi-reasoning-label"><span class="ffvi-reasoning-player"></span> reasoning:</div>
          <div class="ffvi-reasoning-text"></div>
        </div>
      </div>
    `;
    this._elements.narrationBox = narrationBox;
    this._elements.narrationText = narrationBox.querySelector('.ffvi-narration-text');
    this._elements.reasoningContainer = narrationBox.querySelector('.ffvi-reasoning-container');
    this._elements.reasoningPlayer = narrationBox.querySelector('.ffvi-reasoning-player');
    this._elements.reasoningText = narrationBox.querySelector('.ffvi-reasoning-text');
    this._elements.reasoningToggle = narrationBox.querySelector('.ffvi-reasoning-toggle');
    scene.appendChild(narrationBox);

    // Turn indicator
    const turnIndicator = document.createElement('div');
    turnIndicator.className = 'ffvi-turn-indicator';
    turnIndicator.textContent = `Ready (${this._matchData.frames.length} turns)`;
    this._elements.turnIndicator = turnIndicator;
    scene.appendChild(turnIndicator);

    this._elements.battleScene = scene;
    this._container.appendChild(scene);
  }

  _createPlayerPanel(playerName, side) {
    const panel = document.createElement('div');
    panel.className = `ffvi-player-panel ffvi-player-${side}`;
    panel.dataset.player = playerName;

    // Get initial state
    const initialState = this._matchData.frames[0]?.stateBefore || this._matchData.finalState;
    const maxHealth = this._maxHealth;
    const health = initialState.health?.[playerName] ?? maxHealth;
    const potions = initialState.potions?.[playerName] || 0;

    panel.innerHTML = `
      <div class="ffvi-player-name">${this._escapeHtml(playerName)}</div>
      <div class="ffvi-player-sprite">
        <div class="ffvi-sprite-icon">${side === 'left' ? '⚔️' : '🛡️'}</div>
      </div>
      <div class="ffvi-stats">
        <div class="ffvi-hp-container">
          <div class="ffvi-hp-label">HP</div>
          <div class="ffvi-hp-bar">
            <div class="ffvi-hp-fill" style="width: ${(health / maxHealth) * 100}%"></div>
          </div>
          <div class="ffvi-hp-value">${health}/${maxHealth}</div>
        </div>
        <div class="ffvi-potions">
          <span class="ffvi-potion-icon">🧪</span>
          <span class="ffvi-potion-count">${potions}</span>
        </div>
      </div>
    `;

    // Store element references
    this._elements[`player_${playerName}`] = {
      panel,
      hpBar: panel.querySelector('.ffvi-hp-fill'),
      hpValue: panel.querySelector('.ffvi-hp-value'),
      potionCount: panel.querySelector('.ffvi-potion-count'),
      sprite: panel.querySelector('.ffvi-player-sprite')
    };

    return panel;
  }

  _renderInitialState() {
    const firstFrame = this._matchData.frames[0];
    if (firstFrame) {
      this._updateHealthBars(firstFrame.stateBefore);
      this._updatePotions(firstFrame.stateBefore);
    }
  }

  // =========================================================================
  // Private: Updates
  // =========================================================================

  _updateHealthBars(state) {
    const maxHealth = this._maxHealth;

    for (const [player, health] of Object.entries(state.health || {})) {
      const elements = this._elements[`player_${player}`];
      if (!elements) continue;

      const percentage = Math.max(0, (health / maxHealth) * 100);
      elements.hpBar.style.width = `${percentage}%`;
      elements.hpValue.textContent = `${Math.max(0, health)}/${maxHealth}`;

      // Color based on health
      if (percentage > 50) {
        elements.hpBar.className = 'ffvi-hp-fill ffvi-hp-high';
      } else if (percentage > 25) {
        elements.hpBar.className = 'ffvi-hp-fill ffvi-hp-medium';
      } else {
        elements.hpBar.className = 'ffvi-hp-fill ffvi-hp-low';
      }

      // Flash if health changed significantly
      if (health <= 0) {
        elements.panel.classList.add('ffvi-defeated');
      }
    }
  }

  _updatePotions(state) {
    for (const [player, count] of Object.entries(state.potions || {})) {
      const elements = this._elements[`player_${player}`];
      if (!elements) continue;
      elements.potionCount.textContent = count;
    }
  }

  _resolveMaxHealth() {
    const config = this._matchData?.metadata?.gameConfig || {};
    const params = config.params || {};
    const configured = params.max_health;
    if (typeof configured === 'number' && configured > 0) {
      return configured;
    }

    const initialState = this._matchData?.frames[0]?.stateBefore || this._matchData?.finalState;
    const healthValues = Object.values(initialState?.health || {}).filter(
      (value) => typeof value === 'number'
    );
    if (healthValues.length) {
      return Math.max(...healthValues);
    }

    return 100;
  }

  _showAction(player, action, frame) {
    const elements = this._elements[`player_${player}`];
    if (!elements) return;

    // Determine opponent
    const opponent = this._matchData.players.find(p => p !== player);
    const opponentElements = opponent ? this._elements[`player_${opponent}`] : null;

    // Clear previous action
    this._elements.actionDisplay.innerHTML = '';

    // Create action text
    const actionText = document.createElement('div');
    actionText.className = 'ffvi-action-text';

    if (action === 'ATTACK') {
      actionText.innerHTML = `<span class="ffvi-action-name">ATTACK!</span>`;

      // Calculate damage
      const healthBefore = frame.stateBefore.health[opponent] || 0;
      const healthAfter = frame.stateAfter.health[opponent] || 0;
      const damage = healthBefore - healthAfter;

      if (damage > 0) {
        // Show damage number
        const damageText = document.createElement('div');
        damageText.className = 'ffvi-damage-number';
        damageText.textContent = `-${damage}`;
        this._elements.actionDisplay.appendChild(damageText);

        // Flash opponent
        if (opponentElements) {
          opponentElements.panel.classList.add('ffvi-hit');
          setTimeout(() => {
            opponentElements.panel.classList.remove('ffvi-hit');
          }, 300);
        }
      }

      // Animate attacker
      elements.sprite.classList.add('ffvi-attacking');
      setTimeout(() => {
        elements.sprite.classList.remove('ffvi-attacking');
      }, 400);

    } else if (action === 'POTION') {
      actionText.innerHTML = `<span class="ffvi-action-name ffvi-heal">POTION!</span>`;

      // Calculate heal
      const healthBefore = frame.stateBefore.health[player] || 0;
      const healthAfter = frame.stateAfter.health[player] || 0;
      const heal = healthAfter - healthBefore;

      if (heal > 0) {
        const healText = document.createElement('div');
        healText.className = 'ffvi-heal-number';
        healText.textContent = `+${heal}`;
        this._elements.actionDisplay.appendChild(healText);
      }

      // Heal animation
      elements.sprite.classList.add('ffvi-healing');
      setTimeout(() => {
        elements.sprite.classList.remove('ffvi-healing');
      }, 400);

    } else {
      actionText.innerHTML = `<span class="ffvi-action-name">${this._escapeHtml(action)}</span>`;
    }

    this._elements.actionDisplay.appendChild(actionText);

    // Fade out action after delay
    setTimeout(() => {
      actionText.classList.add('ffvi-fade-out');
    }, 600);
  }

  _updateTurnIndicator(turnNumber, frameIndex) {
    const total = this._matchData.frames.length;
    this._elements.turnIndicator.textContent = `Turn ${frameIndex}/${total}`;
  }

  _updateNarration(frame) {
    const player = frame.player;
    const action = frame.action;
    const opponent = this._matchData.players.find(p => p !== player);

    let text = '';

    if (action === 'ATTACK') {
      const damage = (frame.stateBefore.health[opponent] || 0) - (frame.stateAfter.health[opponent] || 0);
      text = `${player} attacks! ${opponent} takes ${damage} damage!`;

      if ((frame.stateAfter.health[opponent] || 0) <= 0) {
        text += ` ${opponent} is defeated!`;
      }
    } else if (action === 'POTION') {
      const heal = (frame.stateAfter.health[player] || 0) - (frame.stateBefore.health[player] || 0);
      const potionsLeft = frame.stateAfter.potions[player] || 0;
      text = `${player} uses a potion! Recovered ${heal} HP! (${potionsLeft} ${potionsLeft === 1 ? 'potion' : 'potions'} left)`;
    } else {
      text = `${player} uses ${action}!`;
    }

    this._elements.narrationText.textContent = text;

    // Update reasoning if available
    if (frame.reasoning) {
      this._elements.reasoningContainer.style.display = 'block';
      this._elements.reasoningPlayer.textContent = player;
      this._elements.reasoningText.textContent = String(frame.reasoning).trim();
    } else {
      this._elements.reasoningContainer.style.display = 'none';
    }
  }

  // =========================================================================
  // Private: Utilities
  // =========================================================================

  _escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

// Register renderer for FixedDamageGame (if registry present).
if (typeof RendererRegistry !== 'undefined') {
  RendererRegistry.register('FixedDamageGame', FixedDamageFFVIRenderer);
}

// Export for module systems, also available as global
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FixedDamageFFVIRenderer;
}
