/**
 * RendererRegistry - Simple registry for mapping games to renderers.
 */
const RendererRegistry = {
  _registry: {},

  /**
   * Register a renderer class for a game name.
   * @param {string} gameName
   * @param {Function} rendererClass
   */
  register(gameName, rendererClass) {
    if (!gameName || !rendererClass) return;
    this._registry[gameName] = rendererClass;
  },

  /**
   * Get the renderer class for a game name.
   * @param {string} gameName
   * @returns {Function | null}
   */
  get(gameName) {
    return this._registry[gameName] || this._registry['*'] || null;
  },

  /**
   * Create a renderer instance for match data.
   * @param {MatchData} matchData
   * @returns {object}
   */
  create(matchData) {
    const RendererClass = this.get(matchData.game);
    if (!RendererClass) {
      throw new Error(`No renderer registered for game: ${matchData.game}`);
    }
    return new RendererClass();
  }
};

if (typeof window !== 'undefined') {
  window.RendererRegistry = RendererRegistry;
}

// Export for module systems, also available as global
if (typeof module !== 'undefined' && module.exports) {
  module.exports = RendererRegistry;
}
