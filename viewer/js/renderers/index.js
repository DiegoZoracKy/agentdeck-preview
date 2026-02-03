/**
 * RendererRegistry - Registry for mapping (game, skin) pairs to renderers.
 */
const RendererRegistry = {
  _registry: {},

  /**
   * Register a renderer class for a game and skin.
   * @param {string} gameName
   * @param {string} skin - Renderer variant (e.g., 'ffvi', 'debug')
   * @param {Function} rendererClass
   */
  register(gameName, skin, rendererClass) {
    if (!gameName || !skin || !rendererClass) return;
    const key = `${gameName}:${skin}`;
    this._registry[key] = rendererClass;
  },

  /**
   * Get the renderer class for a game and skin.
   * @param {string} gameName
   * @param {string} skin
   * @returns {Function | null}
   */
  get(gameName, skin) {
    const key = `${gameName}:${skin}`;
    return this._registry[key] || null;
  },

  /**
   * Get all available skins for a game.
   * @param {string} gameName
   * @returns {string[]} Array of skin names
   */
  getAvailableSkins(gameName) {
    const prefix = `${gameName}:`;
    return Object.keys(this._registry)
      .filter(key => key.startsWith(prefix))
      .map(key => key.substring(prefix.length))
      .sort();
  },

  /**
   * Create a renderer instance for match data and skin.
   * @param {MatchData} matchData
   * @param {string} skin - Renderer variant
   * @returns {object}
   */
  create(matchData, skin) {
    const RendererClass = this.get(matchData.game, skin);
    if (!RendererClass) {
      throw new Error(`No renderer registered for game: ${matchData.game}, skin: ${skin}`);
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
