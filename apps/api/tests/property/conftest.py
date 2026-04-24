"""Hypothesis settings profiles for property-based testing.

Profiles:
  - dev:     50 examples, 30 stateful steps, 200ms deadline — fast local iteration
  - ci:      200 examples, 100 stateful steps, no deadline, derandomized — reproducible CI
  - stress:  10000 examples, 200 stateful steps — deep fuzzing before releases

Activate via ``--hypothesis-profile=<name>`` CLI flag (registered in root conftest).
"""

from hypothesis import settings

settings.register_profile(
    "dev",
    max_examples=50,
    stateful_step_count=30,
    deadline=200,
)
settings.register_profile(
    "ci",
    max_examples=200,
    stateful_step_count=100,
    deadline=None,
    derandomize=True,
)
settings.register_profile(
    "stress",
    max_examples=10000,
    stateful_step_count=200,
)
