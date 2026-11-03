from __future__ import annotations

from typing import Any

from .base import Filter, FilterResult


class StateFilter(Filter):
    """Match the current FSM state against states, state groups, strings or ``None`` (no state).

    ``StateFilter(Form.name, Form.age)``, ``StateFilter(Form)`` (any state of the group),
    ``StateFilter(None)`` or ``StateFilter("*")``.
    """

    def __init__(self, *states: Any) -> None:
        if not states:
            raise ValueError("StateFilter needs at least one state")
        self.states = states

    async def __call__(self, event: Any, raw_state: str | None = None, **data: Any) -> FilterResult:
        for state in self.states:
            if state is None:
                if raw_state is None:
                    return True
            elif state == "*":
                return True
            elif isinstance(state, str):
                if raw_state == state:
                    return True
            elif hasattr(state, "__all_states_names__"):  # StatesGroup subclass
                if raw_state in state.__all_states_names__:
                    return True
            elif getattr(state, "state", None) == "*":
                return True
            elif getattr(state, "state", object()) == raw_state:
                return True
        return False
