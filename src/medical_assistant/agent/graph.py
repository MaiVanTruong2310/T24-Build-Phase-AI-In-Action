"""Medical Assistant Agent Graph.

Centralized in src.agents.graph and re-exported here for backwards compatibility.
"""

from src.agents.graph import (
    agent,
    build_graph,
    checkpointer,
    route_after_critic,
    should_continue,
)

__all__ = [
    "agent",
    "build_graph",
    "checkpointer",
    "route_after_critic",
    "should_continue",
]
