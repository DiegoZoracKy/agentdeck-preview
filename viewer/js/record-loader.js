/**
 * RecordLoader - Load and validate AgentDeck match records
 *
 * Per SPEC-VIEWER §5.1:
 * - V1: MUST reject schema versions < 1.3
 * - V2: MUST extract all `type: "gameplay"` events into frames
 * - V3: MUST preserve frame ordering by `context.turn_index`
 * - V4: MUST normalize state keys to camelCase for JS consumption
 */

const RecordLoader = {
  /**
   * Minimum supported schema version
   */
  MIN_SCHEMA_VERSION: '1.3',

  /**
   * Validate a match record JSON
   * @param {object} json - Raw JSON object
   * @returns {{valid: boolean, errors: string[]}}
   */
  validate(json) {
    const errors = [];

    // Check required top-level fields
    if (!json.schema_version) {
      errors.push('Missing required field: schema_version');
    } else if (this._compareVersions(json.schema_version, this.MIN_SCHEMA_VERSION) < 0) {
      errors.push(`Unsupported schema version: ${json.schema_version}. Requires ${this.MIN_SCHEMA_VERSION}+`);
    }

    if (!json.match_id) errors.push('Missing required field: match_id');
    if (!json.game) errors.push('Missing required field: game');
    if (!Array.isArray(json.players)) errors.push('Missing required field: players (must be array)');
    if (!Array.isArray(json.events)) errors.push('Missing required field: events (must be array)');

    return {
      valid: errors.length === 0,
      errors
    };
  },

  /**
   * Load and parse a match record
   * @param {object} json - Raw JSON object
   * @returns {MatchData}
   * @throws {Error} If validation fails
   */
  load(json) {
    const validation = this.validate(json);
    if (!validation.valid) {
      throw new Error(`Invalid record: ${validation.errors.join(', ')}`);
    }

    // Extract gameplay frames from events
    const frames = this._extractFrames(json.events);
    const lifecycle = this._extractLifecycle(json.events);

    // Warn if no gameplay events
    if (frames.length === 0) {
      console.warn('RecordLoader: No gameplay events found in record');
    }

    // Extract outcome info from metadata
    const matchMeta = json.metadata?.match || {};

    return {
      schemaVersion: json.schema_version,
      matchId: json.match_id,
      game: json.game,
      players: json.players,
      winner: json.winner || null,
      seed: json.seed,
      frames: frames,
      finalState: this._normalizeState(json.final_state || {}),
      metadata: this._normalizeMetadata(json.metadata || {}),
      lifecycle,
      // Outcome details
      outcome: matchMeta.outcome || (json.winner ? 'victory' : 'draw'),
      forfeitReason: matchMeta.forfeit_reason || null,
      forfeitingPlayer: matchMeta.forfeiting_player || null
    };
  },

  /**
   * Load from a File object (drag-drop or file picker)
   * @param {File} file
   * @returns {Promise<MatchData>}
   */
  async loadFromFile(file) {
    const text = await file.text();
    let json;
    try {
      json = JSON.parse(text);
    } catch (_error) {
      throw new Error('Invalid JSON format');
    }
    return this.load(json);
  },

  /**
   * Extract gameplay frames from events array
   * @private
   */
  _extractFrames(events) {
    const frames = [];
    let frameIndex = 0;

    for (const event of events) {
      // Skip non-gameplay events (RC3: unknown types must not crash)
      if (event.type !== 'gameplay') continue;

      const data = event.data || {};
      const context = event.context || {};
      const contextIndex = context.turn_index ?? context.phase_index;
      const dataIndex = data.turn_index ?? data.phase_index;
      const turnIndex =
        typeof contextIndex === 'number'
          ? contextIndex
          : typeof dataIndex === 'number'
            ? dataIndex
            : frameIndex;

      frames.push({
        index: turnIndex,
        turnNumber:
          data.turn_context?.turn_number ||
          data.state_before?.turn ||
          data.metadata?.turn_number ||
          turnIndex + 1,
        player: data.player || 'Unknown',
        action: data.action || 'UNKNOWN',
        reasoning: data.reasoning || null,
        stateBefore: this._normalizeState(data.state_before || {}),
        stateAfter: this._normalizeState(data.state_after || {}),
        timestamp: event.timestamp || 0,
        prompt: this._extractPromptData(data)
      });

      frameIndex += 1;
    }

    // Sort by turn_index to ensure correct order (PI1)
    frames.sort((a, b) => a.index - b.index);

    return frames;
  },

  /**
   * Normalize game state to camelCase (V4)
   * @private
   */
  _normalizeState(state) {
    const normalized = this._normalizeKeys(state || {});
    return {
      health: normalized.health || {},
      potions: normalized.potions || {},
      turn: normalized.turn || 0,
      lastAction: normalized.lastAction || {},
      ...Object.fromEntries(
        Object.entries(normalized).filter(
          ([key]) => !['health', 'potions', 'turn', 'lastAction'].includes(key)
        )
      )
    };
  },

  /**
   * Recursively normalize snake_case object keys to camelCase.
   * @private
   */
  _normalizeKeys(value, preserveObjectKeys = false) {
    if (Array.isArray(value)) {
      return value.map((item) => this._normalizeKeys(item));
    }

    if (value && typeof value === 'object') {
      return Object.fromEntries(
        Object.entries(value).map(([key, nested]) => {
          const normalizedKey = preserveObjectKeys ? key : this._snakeToCamel(key);
          return [
            normalizedKey,
            this._normalizeKeys(nested, this._preservesNestedKeys(normalizedKey))
          ];
        })
      );
    }

    return value;
  },

  /**
   * State fields that are dictionaries keyed by player/model/user-provided ids.
   * @private
   */
  _preservesNestedKeys(key) {
    return ['health', 'potions', 'lastAction', 'scores', 'caseIndex', 'processed'].includes(key);
  },

  /**
   * Convert a snake_case key to camelCase.
   * @private
   */
  _snakeToCamel(key) {
    return String(key).replace(/_([a-z])/g, (_match, letter) => letter.toUpperCase());
  },

  /**
   * Extract prompt data if available
   * @private
   */
  _extractPromptData(data) {
    const prompt = data.prompt || data.metadata || {};

    if (!prompt.prompt_text && !prompt.raw_prompt) {
      return null;
    }

    return {
      promptText: prompt.prompt_text || prompt.raw_prompt || '',
      responseText: prompt.response_text || prompt.raw_response || '',
      duration: prompt.duration || 0
    };
  },

  /**
   * Extract lifecycle events used by debug renderers.
   * @private
   */
  _extractLifecycle(events) {
    return {
      handshakes: this._extractHandshakes(events),
      conclusions: this._extractConclusions(events)
    };
  },

  /**
   * Extract per-player handshake details from lifecycle events.
   * @private
   */
  _extractHandshakes(events) {
    const byPlayer = new Map();
    const eventTypes = new Set([
      'player_handshake_start',
      'player_handshake_complete',
      'player_handshake_abort'
    ]);

    for (const event of events) {
      if (!eventTypes.has(event.type)) continue;

      const data = event.data || {};
      const player = data.player || 'Unknown';
      const ts = Number(event.timestamp || 0);

      if (!byPlayer.has(player)) {
        byPlayer.set(player, {
          player,
          status: 'started',
          accepted: null,
          promptText: '',
          responseText: '',
          normalizedResponse: '',
          reason: null,
          timestamp: ts
        });
      }

      const entry = byPlayer.get(player);
      const promptText = data.prompt_text || data.prompt?.prompt_text || '';
      const responseText =
        data.response_text ||
        data.prompt?.response_text ||
        data.normalized_response ||
        '';

      if (promptText) entry.promptText = promptText;
      if (responseText) entry.responseText = responseText;
      if (data.normalized_response) entry.normalizedResponse = data.normalized_response;
      if (typeof data.accepted === 'boolean') entry.accepted = data.accepted;
      if (data.reason) entry.reason = data.reason;
      if (ts) entry.timestamp = ts;

      if (event.type === 'player_handshake_complete') {
        entry.status = 'complete';
        if (entry.accepted === null) entry.accepted = true;
      } else if (event.type === 'player_handshake_abort') {
        entry.status = 'aborted';
        if (entry.accepted === null) entry.accepted = false;
      }
    }

    return Array.from(byPlayer.values()).sort((a, b) => a.timestamp - b.timestamp);
  },

  /**
   * Extract conclusion/reflection details.
   * @private
   */
  _extractConclusions(events) {
    const entries = [];

    for (const event of events) {
      if (event.type !== 'player_conclusion') continue;
      const data = event.data || {};
      const reflectionText = data.reflection_text || data.reflection || '';
      const responseText = data.response_text || reflectionText || '';
      const promptText = data.prompt_text || data.prompt?.prompt_text || '';

      entries.push({
        player: data.player || 'Unknown',
        reflectionText,
        responseText,
        promptText,
        timestamp: Number(event.timestamp || 0)
      });
    }

    return entries.sort((a, b) => a.timestamp - b.timestamp);
  },

  /**
   * Normalize metadata
   * @private
   */
  _normalizeMetadata(metadata) {
    return {
      startedAt: metadata.started_at || null,
      endedAt: metadata.ended_at || null,
      sessionId: metadata.session_id || null,
      playerSummaries: metadata.player_summaries || [],
      playerConfigs: metadata.player_configs || {},
      gameConfig: metadata.game_config || {},
      match: metadata.match || {}
    };
  },

  /**
   * Compare semantic versions
   * @private
   * @returns {number} -1 if a < b, 0 if equal, 1 if a > b
   */
  _compareVersions(a, b) {
    const partsA = a.split('.').map(Number);
    const partsB = b.split('.').map(Number);

    for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
      const numA = partsA[i] || 0;
      const numB = partsB[i] || 0;
      if (numA < numB) return -1;
      if (numA > numB) return 1;
    }
    return 0;
  }
};

// Export for module systems, also available as global
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RecordLoader;
}
