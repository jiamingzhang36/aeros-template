"""AEROS formal kernel.

The kernel is the v0.4 rule authority. Older YAML/check/receipt layers should
be treated as projections or compatibility views, not independent semantics.
"""
from .core import Action, Evidence, State, TransitionResult, evidence_strength
from .engine import KernelEngine

__all__ = [
    "Action",
    "Evidence",
    "KernelEngine",
    "State",
    "TransitionResult",
    "evidence_strength",
]
