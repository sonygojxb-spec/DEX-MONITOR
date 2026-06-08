"""Shared pytest / Hypothesis configuration.

Registers and loads a default Hypothesis profile with ``max_examples=100`` so
every property-based test runs at least 100 iterations, per the design's
testing strategy. The profile is loaded at import time (collection) so it
applies to the whole suite.
"""

from __future__ import annotations

from hypothesis import settings

# Default profile: at least 100 examples per property (design testing strategy).
settings.register_profile("default", max_examples=100)
settings.load_profile("default")
