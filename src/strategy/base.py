"""State machine base for bot strategy."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from src.utils.logger import log


class State(ABC):
    """Base class for a state in the state machine."""

    name: str = "unnamed"

    def enter(self, ctx: dict):
        """Called when entering this state."""
        pass

    @abstractmethod
    def execute(self, ctx: dict) -> Optional[str]:
        """Execute state logic. Return next state name to transition, or None to stay."""
        pass

    def exit(self, ctx: dict):
        """Called when leaving this state."""
        pass


class StateMachine:
    """Simple finite state machine."""

    def __init__(self):
        self._states: Dict[str, State] = {}
        self.current_state: Optional[State] = None
        self._entered: bool = False

    def add_state(self, state: State):
        """Register a state."""
        self._states[state.name] = state

    def set_initial(self, state_name: str):
        """Set the initial state."""
        self.current_state = self._states[state_name]
        self._entered = False

    def update(self, ctx: dict):
        """Run one tick of the state machine."""
        if self.current_state is None:
            return

        if not self._entered:
            self.current_state.enter(ctx)
            self._entered = True

        next_name = self.current_state.execute(ctx)

        if next_name and next_name != self.current_state.name:
            if next_name not in self._states:
                log.error(f"Unknown state: {next_name}")
                return
            self.current_state.exit(ctx)
            self.current_state = self._states[next_name]
            self.current_state.enter(ctx)
            log.info(f"State -> {next_name}")
