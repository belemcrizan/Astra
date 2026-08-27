from __future__ import annotations

import unittest

from astra_poc.contracts import InvestigationState
from astra_poc.state.machine import (
    InvalidStateTransitionError,
    InvestigationStateMachine,
    LEGAL_TRANSITIONS,
)


class StateMachineTests(unittest.TestCase):
    def test_valid_investigation_lifecycle(self):
        sm = InvestigationStateMachine(initial_state=InvestigationState.OBSERVING)
        self.assertEqual(sm.current_state, InvestigationState.OBSERVING)
        self.assertFalse(sm.is_terminal)

        sm.transition_to(InvestigationState.SIGNAL_DETECTED, trigger="signal_received")
        self.assertEqual(sm.current_state, InvestigationState.SIGNAL_DETECTED)

        sm.transition_to(InvestigationState.TRIAGING, trigger="triage_started")
        self.assertEqual(sm.current_state, InvestigationState.TRIAGING)

        sm.transition_to(InvestigationState.INVESTIGATING, trigger="investigation_opened")
        self.assertEqual(sm.current_state, InvestigationState.INVESTIGATING)

        sm.transition_to(InvestigationState.DECISION_READY, trigger="conclusive_evidence")
        self.assertEqual(sm.current_state, InvestigationState.DECISION_READY)

        sm.transition_to(InvestigationState.ESCALATED, trigger="policy_escalate")
        self.assertEqual(sm.current_state, InvestigationState.ESCALATED)
        self.assertTrue(sm.is_terminal)

        self.assertEqual(len(sm.history), 5)

    def test_illegal_transitions_raise_error(self):
        sm = InvestigationStateMachine(initial_state=InvestigationState.OBSERVING)
        
        # Cannot jump directly from OBSERVING to DECISION_READY or ESCALATED
        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(InvestigationState.DECISION_READY, trigger="invalid_jump")

        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(InvestigationState.ESCALATED, trigger="invalid_jump")

    def test_terminal_state_forbids_outbound_transitions(self):
        sm = InvestigationStateMachine(initial_state=InvestigationState.CLOSED)
        self.assertTrue(sm.is_terminal)
        with self.assertRaises(InvalidStateTransitionError):
            sm.transition_to(InvestigationState.INVESTIGATING, trigger="restart_attempt")

    def test_all_legal_transitions_table_integrity(self):
        for state, targets in LEGAL_TRANSITIONS.items():
            self.assertIsInstance(targets, set)


if __name__ == "__main__":
    unittest.main()
