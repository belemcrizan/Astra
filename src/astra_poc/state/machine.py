from __future__ import annotations

from typing import Any

from ..contracts import InvestigationState, StateTransitionRecord
from ..observability import RunLogger


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal investigation state transition is attempted."""

    def __init__(self, from_state: InvestigationState, to_state: InvestigationState, trigger: str):
        super().__init__(f"Illegal state transition from {from_state.value} to {to_state.value} via trigger '{trigger}'")
        self.from_state = from_state
        self.to_state = to_state
        self.trigger = trigger


# Formal transition table for ASTRA v0.3
LEGAL_TRANSITIONS: dict[InvestigationState, set[InvestigationState]] = {
    InvestigationState.OBSERVING: {
        InvestigationState.SIGNAL_DETECTED,
    },
    InvestigationState.SIGNAL_DETECTED: {
        InvestigationState.TRIAGING,
    },
    InvestigationState.TRIAGING: {
        InvestigationState.INVESTIGATING,
        InvestigationState.CLOSED,
    },
    InvestigationState.INVESTIGATING: {
        InvestigationState.INVESTIGATING,
        InvestigationState.EVIDENCE_INSUFFICIENT,
        InvestigationState.DECISION_READY,
    },
    InvestigationState.EVIDENCE_INSUFFICIENT: {
        InvestigationState.INVESTIGATING,
        InvestigationState.WATCHING,
        InvestigationState.ESCALATED,
        InvestigationState.DEFERRED,
        InvestigationState.HUMAN_REVIEW_REQUIRED,
    },
    InvestigationState.DECISION_READY: {
        InvestigationState.CLOSED,
        InvestigationState.WATCHING,
        InvestigationState.ESCALATED,
        InvestigationState.HUMAN_REVIEW_REQUIRED,
    },
    InvestigationState.HUMAN_REVIEW_REQUIRED: {
        InvestigationState.CLOSED,
        InvestigationState.WATCHING,
        InvestigationState.ESCALATED,
    },
    # Terminal states have no outbound transitions by default
    InvestigationState.CLOSED: set(),
    InvestigationState.WATCHING: set(),
    InvestigationState.ESCALATED: set(),
    InvestigationState.DEFERRED: set(),
}

TERMINAL_STATES: set[InvestigationState] = {
    InvestigationState.CLOSED,
    InvestigationState.WATCHING,
    InvestigationState.ESCALATED,
    InvestigationState.DEFERRED,
}


class InvestigationStateMachine:
    """Formal Investigation State Machine for ASTRA v0.3.
    
    Enforces explicit lifecycle states and bounded state transitions.
    Illegal transitions raise InvalidStateTransitionError and emit telemetry.
    """

    def __init__(
        self,
        initial_state: InvestigationState = InvestigationState.OBSERVING,
        logger: RunLogger | None = None,
    ):
        self._current_state = initial_state
        self._history: list[StateTransitionRecord] = []
        self._logger = logger

    @property
    def current_state(self) -> InvestigationState:
        return self._current_state

    @property
    def history(self) -> list[StateTransitionRecord]:
        return list(self._history)

    @property
    def is_terminal(self) -> bool:
        return self._current_state in TERMINAL_STATES

    def can_transition_to(self, target_state: InvestigationState) -> bool:
        allowed = LEGAL_TRANSITIONS.get(self._current_state, set())
        return target_state in allowed

    def transition_to(
        self,
        target_state: InvestigationState,
        trigger: str,
        metadata: dict[str, Any] | None = None,
    ) -> StateTransitionRecord:
        if not self.can_transition_to(target_state):
            if self._logger:
                self._logger.emit(
                    "illegal_state_transition_attempted",
                    from_state=self._current_state.value,
                    target_state=target_state.value,
                    trigger=trigger,
                    metadata=metadata or {},
                )
            raise InvalidStateTransitionError(self._current_state, target_state, trigger)

        record = StateTransitionRecord(
            from_state=self._current_state,
            to_state=target_state,
            trigger=trigger,
            metadata=metadata or {},
        )
        self._history.append(record)
        old_state = self._current_state
        self._current_state = target_state

        if self._logger:
            self._logger.emit(
                "state_transition",
                from_state=old_state.value,
                to_state=target_state.value,
                trigger=trigger,
                is_terminal=self.is_terminal,
                metadata=metadata or {},
            )

        return record
