from SpotiFLAC.core.lyrics import (
    DEFAULT_LYRICS_PROVIDERS,
    _best_jiosaavn_result,
)


def _hit(track_id: str, duration: str, has_lyrics: str = "true") -> dict:
    """Build a JioSaavn result with configurable duration and lyrics availability."""
    return {
        "id": track_id,
        "more_info": {"duration": duration, "has_lyrics": has_lyrics},
    }


def test_jiosaavn_is_enabled_by_default() -> None:
    """Verify the default lyrics provider chain includes JioSaavn."""
    assert "jiosaavn" in DEFAULT_LYRICS_PROVIDERS


def test_jiosaavn_picks_closest_lyric_match() -> None:
    """Verify selection favors the closest duration among results with lyrics."""
    found = _best_jiosaavn_result(
        [
            _hit("far", "260"),
            _hit("closest", "262"),
            _hit("no-lyrics", "261", "false"),
        ],
        262,
    )

    assert found is not None
    assert found["id"] == "closest"
