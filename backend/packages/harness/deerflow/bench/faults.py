"""Which defects are planted in this process.

Both halves of the corpus come from one build. A clean run is what a reader measures its
per-project baselines from — the latency line, the tool-evidence rate, the instruction
floor — and a faulted run is scored against them; a corpus with no clean half makes the
faulted behaviour its own baseline, and nothing deviates.
"""

import os

ACTIVE = frozenset(f for f in os.environ.get("ORDERS_FAULTS", "").split(",") if f)


def on(fault: str) -> bool:
    return fault in ACTIVE
