"""Visibility audit for the protected Hangman product holdout."""

import json

from agentdeck.games.examples.hangman import HangmanGame


def test_hangman_player_view_never_exposes_the_secret_word():
    game = HangmanGame(word_list=["AGENT"])
    state = game.setup(["Alice", "Bob"], seed=7)

    view = game.get_view(state, "Alice")

    assert "secret_word" not in view
    assert state["secret_word"] not in json.dumps(view)
    assert view["board"] == "_ _ _ _ _"
