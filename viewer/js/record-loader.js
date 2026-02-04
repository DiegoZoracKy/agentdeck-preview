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
    const json = JSON.parse(text);
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
    return {
      health: state.health || {},
      potions: state.potions || {},
      turn: state.turn || 0,
      lastAction: state.last_action || {}
    };
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
