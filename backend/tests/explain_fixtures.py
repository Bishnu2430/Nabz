"""The shared explanation fixtures live in the app, so the safety console can run the red-team suite too."""

from app.explain.fixtures import GOOD, GOOD_HI, good, passages, payload, with_text

__all__ = ["GOOD", "GOOD_HI", "good", "passages", "payload", "with_text"]
