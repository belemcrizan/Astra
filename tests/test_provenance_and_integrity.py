from __future__ import annotations

import unittest
from astra_poc.provenance.graph import DecisionProvenanceGraph
from astra_poc.provenance.integrity import IntegrityChain
from astra_poc.contracts import IntegrityChainRecord


class ProvenanceAndIntegrityTests(unittest.TestCase):
    def test_provenance_graph_constructs_dag_and_mermaid(self):
        graph = DecisionProvenanceGraph("inv-test-123")
        graph.add_node("obs-1", "observation", "Anomaly at t=600")
        graph.add_node("H1", "hypothesis", "H1: Transient Noise")
        graph.add_edge("obs-1", "H1", "generated")

        graph.add_node("act-1", "action", "Step 1: RUN_PELT")
        graph.add_edge("H1", "act-1", "selected_because")
        graph.add_node("ev-1", "evidence", "Segment breaks = 2")
        graph.add_edge("act-1", "ev-1", "produced")
        graph.add_edge("ev-1", "H1", "contradicts")

        contract = graph.to_contract()
        self.assertEqual(len(contract.nodes), 4)
        self.assertEqual(len(contract.edges), 4)
        self.assertIn("graph TD", contract.mermaid_diagram)
        self.assertIn("obs-1", contract.mermaid_diagram)

    def test_integrity_chain_detects_hash_tampering(self):
        chain = IntegrityChain()
        rec0 = chain.append_event("genesis", {"status": "init"})
        rec1 = chain.append_event("test_exec", {"test": "PELT"})
        rec2 = chain.append_event("decision", {"decision": "ESCALATE"})

        is_valid, msg = IntegrityChain.verify_chain(chain.records)
        self.assertTrue(is_valid)

        # Tamper with previous_hash in rec2
        tampered_rec2 = IntegrityChainRecord(
            step_index=rec2.step_index,
            event_hash=rec2.event_hash,
            previous_hash="tampered_hash_12345",
            payload_summary=rec2.payload_summary,
            timestamp=rec2.timestamp,
        )
        tampered_chain = [rec0, rec1, tampered_rec2]
        is_tampered_valid, tamper_msg = IntegrityChain.verify_chain(tampered_chain)
        self.assertFalse(is_tampered_valid)
        self.assertIn("Broken hash linkage", tamper_msg)


if __name__ == "__main__":
    unittest.main()
