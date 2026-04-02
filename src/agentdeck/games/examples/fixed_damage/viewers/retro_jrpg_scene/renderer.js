/**
 * CombatRetroJrpgSceneRenderer - Retro JRPG-inspired battle scene renderer
 *
 * Per SPEC-VIEWER §5.3:
 * - R1: init() MUST be callable multiple times (re-init for new match)
 * - R2: renderFrame() MUST handle any valid GameplayFrame
 * - R3: destroy() MUST remove all DOM elements added by renderer
 * - R4: Renderers MUST NOT modify MatchData or GameplayFrame objects
 */

class CombatRetroJrpgSceneRenderer {
  constructor() {
    this._container = null;
    this._matchData = null;
    this._elements = {};
    this._players = [];
    this._playerSides = {};
    this._maxHealth = 100;
    this._animationTimeouts = [];
  }

  /**
   * Initialize renderer in container
   * @param {HTMLElement} container
   * @param {MatchData} matchData
   */
  init(container, matchData) {
    this.destroy();

    this._container = container;
    this._matchData = matchData;
    this._players = matchData.players || [];
    this._playerSides = {
      [this._players[0]]: 'left',
      [this._players[1]]: 'right'
    };

    this._maxHealth = this._resolveMaxHealth();
    this._createScene();
    this._renderInitialState();
  }

  /**
   * Render a gameplay frame
   * @param {GameplayFrame} frame
   */
  renderFrame(frame) {
    if (!this._container) return;

    this._clearVictoryOverlay();
    this._updateTurn(frame.turnNumber, frame.index + 1);
    this._updateStatus(frame.stateAfter);
    this._updateMessage(frame);
    this._updateReasoning(frame);
    this._triggerAnimation(frame);
  }

  /**
   * Render victory screen
   * @param {string | null} winner
   * @param {GameState} finalState
   * @param {object} outcomeInfo - Optional outcome details
   */
  renderVictory(winner, finalState, outcomeInfo = {}) {
    if (!this._container || !this._elements.scene) return;

    const overlay = document.createElement('div');
    overlay.className = 'scene-victory';

    const { outcome, forfeitReason, forfeitingPlayer } = outcomeInfo;

    if (winner) {
      if (outcome === 'forfeit' && forfeitingPlayer) {
        const reasonText = this._formatForfeitReason(forfeitReason);
        overlay.innerHTML = `
          <div class="scene-victory-title">FORFEIT</div>
          <div class="scene-victory-winner">${this._escapeHtml(winner)} wins</div>
          <div class="scene-victory-sub">${this._escapeHtml(forfeitingPlayer)} ${reasonText}</div>
        `;
      } else {
        overlay.innerHTML = `
          <div class="scene-victory-title">VICTORY</div>
          <div class="scene-victory-winner">${this._escapeHtml(winner)}</div>
          <div class="scene-victory-sub">Final HP: ${finalState.health[winner] || 0}</div>
        `;
      }
    } else {
      overlay.innerHTML = `
        <div class="scene-victory-title">DRAW</div>
        <div class="scene-victory-sub">Both combatants fell</div>
      `;
    }

    this._elements.scene.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('visible'));
  }

  /**
   * Cleanup resources
   */
  destroy() {
    this._clearAnimationTimeouts();
    if (this._container && this._elements.scene) {
      this._container.removeChild(this._elements.scene);
    }
    this._container = null;
    this._matchData = null;
    this._elements = {};
    this._players = [];
    this._playerSides = {};
  }

  // =========================================================================
  // Private: Scene Creation
  // =========================================================================

  _createScene() {
    const scene = document.createElement('div');
    scene.className = 'retro-jrpg-scene';

    // Message box (top)
    const message = document.createElement('div');
    message.className = 'scene-message';

    const messageLeft = document.createElement('div');
    messageLeft.className = 'scene-message-left';

    const actionEl = document.createElement('div');
    actionEl.className = 'scene-action';
    actionEl.textContent = 'READY';

    const detailEl = document.createElement('div');
    detailEl.className = 'scene-detail';
    detailEl.textContent = 'Press Play to begin';

    const messageRight = document.createElement('div');
    messageRight.className = 'scene-message-right';

    const playbackStatusEl = document.createElement('div');
    playbackStatusEl.className = 'scene-playback-status scene-message-meta is-ready';
    playbackStatusEl.textContent = 'READY';

    const turnEl = document.createElement('div');
    turnEl.className = 'scene-turn scene-message-meta';
    turnEl.textContent = 'Turn 0/0';

    messageLeft.appendChild(actionEl);
    messageLeft.appendChild(detailEl);
    messageRight.appendChild(playbackStatusEl);
    messageRight.appendChild(turnEl);
    message.appendChild(messageLeft);
    message.appendChild(messageRight);

    // Arena
    const arena = document.createElement('div');
    arena.className = 'scene-arena';

    const leftKnight = this._createKnight(this._players[0] || 'Player 1', 'left');
    const rightKnight = this._createKnight(this._players[1] || 'Player 2', 'right');

    arena.appendChild(leftKnight);
    arena.appendChild(rightKnight);

    const reasoningBubble = document.createElement('div');
    reasoningBubble.className = 'scene-reasoning hidden tail-left';

    const reasoningHeader = document.createElement('div');
    reasoningHeader.className = 'scene-reasoning-header';
    reasoningHeader.textContent = 'Reasoning';

    const reasoningText = document.createElement('div');
    reasoningText.className = 'scene-reasoning-text';
    reasoningText.textContent = 'No reasoning provided.';

    reasoningBubble.appendChild(reasoningHeader);
    reasoningBubble.appendChild(reasoningText);
    arena.appendChild(reasoningBubble);

    const highlightEl = document.createElement('div');
    highlightEl.className = 'scene-highlight';

    const highlightIconEl = document.createElement('span');
    highlightIconEl.className = 'scene-highlight-icon';
    highlightIconEl.textContent = '';

    const highlightTextEl = document.createElement('span');
    highlightTextEl.className = 'scene-highlight-text';
    highlightTextEl.textContent = '';

    highlightEl.appendChild(highlightIconEl);
    highlightEl.appendChild(highlightTextEl);
    arena.appendChild(highlightEl);

    // Status bar (bottom)
    const status = document.createElement('div');
    status.className = 'scene-status';

    const leftStatus = this._createStatusCard(this._players[0] || 'Player 1', 'left');
    const rightStatus = this._createStatusCard(this._players[1] || 'Player 2', 'right');

    status.appendChild(leftStatus);
    status.appendChild(rightStatus);

    scene.appendChild(message);
    scene.appendChild(arena);
    scene.appendChild(status);

    this._container.appendChild(scene);

    this._elements = {
      scene,
      actionEl,
      detailEl,
      playbackStatusEl,
      turnEl,
      reasoningBubble,
      reasoningText,
      highlightEl,
      highlightIconEl,
      highlightTextEl,
      knights: {
        [this._players[0]]: leftKnight,
        [this._players[1]]: rightKnight
      },
      status: {
        [this._players[0]]: leftStatus,
        [this._players[1]]: rightStatus
      }
    };
  }

  _createKnight(playerName, side) {
    const knight = document.createElement('div');
    knight.className = `scene-knight scene-${side}`;
    knight.dataset.player = playerName;
    knight.dataset.side = side;

    const crest = document.createElement('div');
    crest.className = 'scene-crest';

    const logoAsset = this._getLogoAsset(playerName);
    let logo = null;
    if (logoAsset) {
      logo = document.createElement('img');
      logo.className = 'scene-logo-img';
      logo.src = logoAsset;
      logo.alt = playerName;
      logo.title = playerName;
    } else {
      logo = document.createElement('div');
      logo.className = 'scene-logo';
      logo.textContent = this._shortLabel(playerName);
    }

    const hit = document.createElement('div');
    hit.className = 'scene-hit';

    crest.appendChild(logo);
    crest.appendChild(hit);

    const name = document.createElement('div');
    name.className = 'scene-name';

    const nameText = document.createElement('div');
    nameText.className = 'scene-name-text';
    nameText.textContent = playerName;
    name.appendChild(nameText);

    const modelName = this._getModelName(playerName);
    if (modelName) {
      const modelText = document.createElement('div');
      modelText.className = 'scene-model';
      modelText.textContent = `(${modelName})`;
      modelText.title = modelName;
      name.appendChild(modelText);
    }

    knight.appendChild(crest);
    knight.appendChild(name);

    return knight;
  }

  _createStatusCard(playerName, side) {
    const card = document.createElement('div');
    card.className = `scene-status-card scene-${side}`;
    card.dataset.player = playerName;

    const name = document.createElement('div');
    name.className = 'scene-status-name';
    name.textContent = playerName;

    const modelName = this._getModelName(playerName);
    let modelLine = null;
    if (modelName) {
      modelLine = document.createElement('div');
      modelLine.className = 'scene-status-model';
      modelLine.textContent = `(${modelName})`;
      modelLine.title = modelName;
    }

    const hpRow = document.createElement('div');
    hpRow.className = 'scene-status-hp';

    const hpLabel = document.createElement('span');
    hpLabel.className = 'scene-status-label';
    hpLabel.textContent = 'HP';

    const hpBar = document.createElement('div');
    hpBar.className = 'scene-hp-bar';

    const hpFill = document.createElement('div');
    hpFill.className = 'scene-hp-fill';
    hpBar.appendChild(hpFill);

    const hpValue = document.createElement('span');
    hpValue.className = 'scene-hp-value';
    hpValue.textContent = '0/0';

    hpRow.appendChild(hpLabel);
    hpRow.appendChild(hpBar);
    hpRow.appendChild(hpValue);

    const potions = document.createElement('div');
    potions.className = 'scene-status-potions';
    potions.textContent = 'Potions: 0';

    card.appendChild(name);
    if (modelLine) {
      card.appendChild(modelLine);
    }
    card.appendChild(hpRow);
    card.appendChild(potions);

    // Store references for updates
    card._hpFill = hpFill;
    card._hpValue = hpValue;
    card._potions = potions;

    return card;
  }

  // =========================================================================
  // Private: Updates
  // =========================================================================

  _renderInitialState() {
    const first = this._matchData.frames && this._matchData.frames[0];
    if (first) {
      this._updateStatus(first.stateBefore);
      this._updateTurn(first.turnNumber, 0);
    } else if (this._matchData.finalState) {
      this._updateStatus(this._matchData.finalState);
    }
  }

  _updateStatus(state) {
    const health = state.health || {};
    const potions = state.potions || {};

    this._players.forEach((player) => {
      const card = this._elements.status[player];
      if (!card) return;

      const hp = health[player] ?? 0;
      const pot = potions[player] ?? 0;
      const percent = this._maxHealth > 0 ? (hp / this._maxHealth) * 100 : 0;

      card._hpFill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
      card._hpValue.textContent = `${hp}/${this._maxHealth}`;
      card._potions.textContent = `Potions: ${pot}`;

      card._hpFill.classList.remove('low', 'critical');
      if (percent <= 25) {
        card._hpFill.classList.add('critical');
      } else if (percent <= 50) {
        card._hpFill.classList.add('low');
      }
    });
  }

  _updateMessage(frame) {
    if (!frame) return;

    const action = (frame.action || 'READY').toUpperCase();
    const attacker = frame.player || 'Player';
    const target = this._getTarget(attacker);
    const detailEl = this._elements.detailEl;
    if (!detailEl) return;

    // Build styled detail text safely via text nodes/spans.
    detailEl.replaceChildren();
    const appendText = (text) => detailEl.appendChild(document.createTextNode(text));
    const appendToken = (text, className) => {
      const span = document.createElement('span');
      span.className = className;
      span.textContent = text;
      detailEl.appendChild(span);
    };

    if (action === 'ATTACK' && target) {
      const before = frame.stateBefore?.health?.[target] ?? 0;
      const after = frame.stateAfter?.health?.[target] ?? 0;
      const dmg = Math.max(0, before - after);

      appendText(`${attacker} `);
      appendToken('attacks', 'scene-detail-action');
      appendText(` ${target}`);
      if (dmg) {
        appendText(' (');
        appendToken(`-${dmg}`, 'scene-detail-effect damage');
        appendText(')');
      }
    } else if (action === 'POTION') {
      const before = frame.stateBefore?.health?.[attacker] ?? 0;
      const after = frame.stateAfter?.health?.[attacker] ?? 0;
      const heal = Math.max(0, after - before);

      appendText(`${attacker} uses `);
      appendToken('POTION', 'scene-detail-action');
      if (heal) {
        appendText(' (');
        appendToken(`+${heal}`, 'scene-detail-effect heal');
        appendText(')');
      }
    } else {
      appendText(`${attacker} `);
      appendToken('acts', 'scene-detail-action');
    }

    const actionEl = this._elements.actionEl;
    if (actionEl) {
      actionEl.textContent = action;
      actionEl.classList.remove('is-attack', 'is-potion');
      if (action === 'ATTACK') {
        actionEl.classList.add('is-attack');
      } else if (action === 'POTION') {
        actionEl.classList.add('is-potion');
      }
    }
  }

  _updateReasoning(frame) {
    const bubble = this._elements.reasoningBubble;
    const textEl = this._elements.reasoningText;
    if (!bubble || !textEl) return;

    const player = frame.player || this._players[0];
    const side = this._playerSides[player] || 'left';
    bubble.classList.remove('tail-left', 'tail-right');
    bubble.classList.add(side === 'left' ? 'tail-left' : 'tail-right');

    const reasoning = frame.reasoning;
    if (reasoning && String(reasoning).trim().length > 0) {
      bubble.classList.remove('hidden');
      bubble.classList.remove('empty');
      textEl.textContent = String(reasoning);
    } else {
      bubble.classList.add('empty');
      bubble.classList.add('hidden');
      textEl.textContent = 'No reasoning provided.';
    }
  }

  _updateTurn(turnNumber, frameNumber) {
    const total = this._matchData.frames.length || 0;
    const turnText = turnNumber ? `Turn ${turnNumber}/${total}` : `Turn ${frameNumber}/${total}`;
    this._elements.turnEl.textContent = turnText;
  }

  setPlaybackStatus(status) {
    const el = this._elements.playbackStatusEl;
    if (!el) return;

    const normalized = String(status || 'Ready').trim();
    const upper = normalized.toUpperCase();
    el.textContent = upper;

    el.classList.remove('is-ready', 'is-playing', 'is-paused', 'is-complete', 'is-error');
    if (upper === 'PLAYING') {
      el.classList.add('is-playing');
      return;
    }
    if (upper === 'PAUSED') {
      el.classList.add('is-paused');
      return;
    }
    if (upper === 'COMPLETE') {
      el.classList.add('is-complete');
      return;
    }
    if (upper === 'ERROR') {
      el.classList.add('is-error');
      return;
    }
    el.classList.add('is-ready');
  }

  setActiveHighlight(highlight) {
    const highlightEl = this._elements.highlightEl;
    const highlightIconEl = this._elements.highlightIconEl;
    const highlightTextEl = this._elements.highlightTextEl;
    if (!highlightEl || !highlightIconEl || !highlightTextEl) return;

    if (!highlight || !highlight.label) {
      highlightEl.classList.remove('visible');
      highlightEl.removeAttribute('data-kind');
      highlightIconEl.textContent = '';
      highlightTextEl.textContent = '';
      return;
    }

    highlightEl.classList.add('visible');
    if (highlight.kind) highlightEl.dataset.kind = highlight.kind;
    else highlightEl.removeAttribute('data-kind');
    highlightIconEl.textContent = highlight.icon || '';
    highlightTextEl.textContent = highlight.label;
  }

  _triggerAnimation(frame) {
    this._clearAnimationTimeouts();

    const attacker = frame.player;
    const target = this._getTarget(attacker);
    const action = frame.action;

    const attackerEl = this._elements.knights[attacker];
    const targetEl = this._elements.knights[target];

    if (attackerEl) {
      attackerEl.classList.remove('is-attacking', 'is-healing');
      void attackerEl.offsetWidth;
    }
    if (targetEl) {
      targetEl.classList.remove('is-hit');
      void targetEl.offsetWidth;
    }

    if (action === 'ATTACK' && attackerEl && targetEl) {
      attackerEl.classList.add('is-attacking');
      targetEl.classList.add('is-hit');
    } else if (action === 'POTION' && attackerEl) {
      attackerEl.classList.add('is-healing');
    }

    const timeout = setTimeout(() => {
      if (attackerEl) attackerEl.classList.remove('is-attacking', 'is-healing');
      if (targetEl) targetEl.classList.remove('is-hit');
    }, 600);
    this._animationTimeouts.push(timeout);
  }

  _clearVictoryOverlay() {
    if (!this._elements.scene) return;
    const overlay = this._elements.scene.querySelector('.scene-victory');
    if (overlay) overlay.remove();
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

  _resolveMaxHealth() {
    let max = 100;
    const frames = this._matchData.frames || [];

    frames.forEach((frame) => {
      const before = frame.stateBefore?.health || {};
      const after = frame.stateAfter?.health || {};
      Object.values(before).forEach((value) => {
        if (typeof value === 'number') max = Math.max(max, value);
      });
      Object.values(after).forEach((value) => {
        if (typeof value === 'number') max = Math.max(max, value);
      });
    });

    return max || 100;
  }

  _getTarget(attacker) {
    return this._players.find((player) => player !== attacker) || this._players[0];
  }

  _shortLabel(name) {
    if (!name) return '??';
    const clean = name.replace(/[^a-zA-Z0-9]/g, '');
    return clean.slice(0, 3).toUpperCase() || name.slice(0, 3).toUpperCase();
  }

  _getLogoAsset(playerName) {
    const modelName = (this._getModelName(playerName) || '').toLowerCase();
    const playerLabel = (playerName || '').toLowerCase();
    const key = `${modelName} ${playerLabel}`;

    if (/(openai|gpt|4o|o1|o3)/.test(key)) {
      return this._assetUrl('openai_logo_knight.png');
    }
    if (/(anthropic|claude)/.test(key)) {
      return this._assetUrl('claude_logo_knight.png');
    }
    if (/(gemini|google)/.test(key)) {
      return this._assetUrl('gemini_logo_knight.png');
    }

    return this._assetUrl('player_logo_fallback.png');
  }

  _assetUrl(fileName) {
    return `../src/agentdeck/games/examples/fixed_damage/viewers/retro_jrpg_scene/assets/${fileName}`;
  }

  _getModelName(playerName) {
    const summaries = this._matchData?.metadata?.playerSummaries || [];
    const summary = summaries.find((entry) => entry.name === playerName) || {};
    const summaryModel =
      summary.model || summary.model_name || summary.modelName || summary.model_id || null;

    if (summaryModel) return summaryModel;

    const configs = this._matchData?.metadata?.playerConfigs || {};
    const config = configs[playerName] || {};
    return config.model || config.model_name || config.modelName || null;
  }

  _clearAnimationTimeouts() {
    this._animationTimeouts.forEach((timeout) => clearTimeout(timeout));
    this._animationTimeouts = [];
  }

  _escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
}

// Register renderer for the bundled combat games (if registry present).
if (typeof RendererRegistry !== 'undefined') {
  RendererRegistry.register('FixedDamageGame', 'retro_jrpg_scene', CombatRetroJrpgSceneRenderer);
  RendererRegistry.register('VariableDamageGame', 'retro_jrpg_scene', CombatRetroJrpgSceneRenderer);
}

// Export for module systems, also available as global
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CombatRetroJrpgSceneRenderer;
}
