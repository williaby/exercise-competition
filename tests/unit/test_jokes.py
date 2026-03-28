"""Unit tests for the jokes module."""

from __future__ import annotations

from exercise_competition.services.jokes import NICK_JOKES, get_random_joke


class TestJokes:
    """Tests for joke selection."""

    def test_get_random_joke_returns_string(self) -> None:
        joke = get_random_joke()
        assert isinstance(joke, str)

    def test_get_random_joke_from_collection(self) -> None:
        joke = get_random_joke()
        assert joke in NICK_JOKES

    def test_jokes_collection_not_empty(self) -> None:
        assert len(NICK_JOKES) > 0

    def test_all_jokes_are_nonempty_strings(self) -> None:
        for joke in NICK_JOKES:
            assert isinstance(joke, str)
            assert len(joke.strip()) > 0

    def test_randomness_produces_variety(self) -> None:
        """Multiple calls should eventually return different jokes."""
        results = {get_random_joke() for _ in range(50)}
        assert len(results) > 1
