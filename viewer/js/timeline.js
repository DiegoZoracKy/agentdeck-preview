/**
 * Timeline - Core playback engine for AgentDeck match replay
 *
 * Per SPEC-VIEWER §5.2:
 * - T1: play() MUST emit frames at intervals of baseDelay / speed
 * - T2: step() MUST emit exactly one frame and pause
 * - T3: seek() MUST clamp to valid frame range [0, totalFrames-1]
 * - T4: Frame callbacks MUST receive complete GameplayFrame data
 * - T5: onEnd MUST fire after last frame with winner from MatchData
 */

class Timeline {
  /**
   * @param {MatchData} matchData - Normalized match data from RecordLoader
   */
  constructor(matchData) {
    this._matchData = matchData;
    this._frames = matchData.frames;
    this._currentFrame = -1; // -1 means "before first frame"
    this._isPlaying = false;
    this._speed = 1;
    this._baseDelay = 1000; // 1 second between frames at 1x speed
    this._playbackTimer = null;

    // Event callbacks
    this._frameCallbacks = [];
    this._endCallbacks = [];
    this._stateChangeCallbacks = [];
  }

  // =========================================================================
  // Playback Control
  // =========================================================================

  /**
   * Start or resume playback
   */
  play() {
    if (this._isPlaying) return;
    if (this._currentFrame >= this._frames.length - 1) {
      // At end, restart from beginning
      this._currentFrame = -1;
    }

    this._isPlaying = true;
    this._emitStateChange();
    this._scheduleNextFrame();
  }

  /**
   * Pause playback
   */
  pause() {
    if (!this._isPlaying) return;

    this._isPlaying = false;
    if (this._playbackTimer) {
      clearTimeout(this._playbackTimer);
      this._playbackTimer = null;
    }
    this._emitStateChange();
  }

  /**
   * Step forward or backward one frame
   * @param {1 | -1} direction - 1 for forward, -1 for backward
   */
  step(direction = 1) {
    this.pause();

    const newFrame = this._currentFrame + direction;
    if (newFrame >= 0 && newFrame < this._frames.length) {
      this._currentFrame = newFrame;
      this._emitFrame(this._frames[this._currentFrame]);
      this._emitStateChange();

      // Check for end
      if (this._currentFrame === this._frames.length - 1) {
        this._emitEnd();
      }
    }
  }

  /**
   * Jump to specific frame
   * @param {number} frameIndex - Target frame index
   */
  seek(frameIndex) {
    // T3: Clamp to valid range
    const clampedIndex = Math.max(0, Math.min(frameIndex, this._frames.length - 1));

    if (clampedIndex !== this._currentFrame && this._frames.length > 0) {
      this._currentFrame = clampedIndex;
      this._emitFrame(this._frames[this._currentFrame]);
      this._emitStateChange();

      // Check for end
      if (this._currentFrame === this._frames.length - 1 && !this._isPlaying) {
        this._emitEnd();
      }
    }
  }

  /**
   * Set playback speed multiplier
   * @param {number} multiplier - Speed (0.5, 1, 2, 4, etc.)
   */
  setSpeed(multiplier) {
    this._speed = Math.max(0.1, Math.min(multiplier, 10));
    this._emitStateChange();

    // If playing, reschedule with new speed
    if (this._isPlaying) {
      if (this._playbackTimer) {
        clearTimeout(this._playbackTimer);
      }
      this._scheduleNextFrame();
    }
  }

  /**
   * Reset to beginning
   */
  reset() {
    this.pause();
    this._currentFrame = -1;
    this._emitStateChange();
  }

  // =========================================================================
  // State (Read-only)
  // =========================================================================

  get currentFrame() {
    return this._currentFrame;
  }

  get totalFrames() {
    return this._frames.length;
  }

  get isPlaying() {
    return this._isPlaying;
  }

  get speed() {
    return this._speed;
  }

  get matchData() {
    return this._matchData;
  }

  /**
   * Get current frame data (or null if before first frame)
   */
  get currentFrameData() {
    if (this._currentFrame < 0 || this._currentFrame >= this._frames.length) {
      return null;
    }
    return this._frames[this._currentFrame];
  }

  // =========================================================================
  // Event Subscriptions
  // =========================================================================

  /**
   * Subscribe to frame events
   * @param {(frame: GameplayFrame) => void} callback
   */
  onFrame(callback) {
    this._frameCallbacks.push(callback);
  }

  /**
   * Unsubscribe from frame events
   */
  offFrame(callback) {
    const index = this._frameCallbacks.indexOf(callback);
    if (index !== -1) {
      this._frameCallbacks.splice(index, 1);
    }
  }

  /**
   * Subscribe to end event
   * @param {(winner: string | null) => void} callback
   */
  onEnd(callback) {
    this._endCallbacks.push(callback);
  }

  /**
   * Unsubscribe from end event
   */
  offEnd(callback) {
    const index = this._endCallbacks.indexOf(callback);
    if (index !== -1) {
      this._endCallbacks.splice(index, 1);
    }
  }

  /**
   * Subscribe to state changes (play/pause/seek/speed)
   * @param {() => void} callback
   */
  onStateChange(callback) {
    this._stateChangeCallbacks.push(callback);
  }

  /**
   * Unsubscribe from state changes
   */
  offStateChange(callback) {
    const index = this._stateChangeCallbacks.indexOf(callback);
    if (index !== -1) {
      this._stateChangeCallbacks.splice(index, 1);
    }
  }

  // =========================================================================
  // Private Methods
  // =========================================================================

  /**
   * Schedule the next frame emission
   * @private
   */
  _scheduleNextFrame() {
    if (!this._isPlaying) return;

    const delay = this._baseDelay / this._speed;

    this._playbackTimer = setTimeout(() => {
      this._advanceFrame();
    }, delay);
  }

  /**
   * Advance to next frame
   * @private
   */
  _advanceFrame() {
    if (!this._isPlaying) return;

    this._currentFrame++;

    if (this._currentFrame < this._frames.length) {
      this._emitFrame(this._frames[this._currentFrame]);
      this._emitStateChange();
      this._scheduleNextFrame();
    } else {
      // Reached end
      this._currentFrame = this._frames.length - 1;
      this._isPlaying = false;
      this._emitStateChange();
      this._emitEnd();
    }
  }

  /**
   * Emit frame to all listeners
   * @private
   */
  _emitFrame(frame) {
    for (const callback of this._frameCallbacks) {
      try {
        callback(frame);
      } catch (err) {
        // RI4: Renderer failures MUST NOT crash Timeline
        console.error('Timeline: Frame callback error:', err);
      }
    }
  }

  /**
   * Emit end event
   * @private
   */
  _emitEnd() {
    for (const callback of this._endCallbacks) {
      try {
        callback(this._matchData.winner);
      } catch (err) {
        console.error('Timeline: End callback error:', err);
      }
    }
  }

  /**
   * Emit state change event
   * @private
   */
  _emitStateChange() {
    for (const callback of this._stateChangeCallbacks) {
      try {
        callback();
      } catch (err) {
        console.error('Timeline: State change callback error:', err);
      }
    }
  }
}

// Export for module systems, also available as global
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Timeline;
}
