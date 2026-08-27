from __future__ import annotations

from typing import Any
import json

from ..contracts import (
    DecisionProvenanceEdge,
    DecisionProvenanceGraphData,
    DecisionProvenanceNode,
)


class DecisionProvenanceGraph:
    """Constructs a formal Decision Provenance Graph (DAG) for an investigation.
    
    Traces the exact causal lineage from observation -> hypotheses -> candidate utility
    evaluations -> selected tests -> observed evidence -> falsification -> final decision.
    """

    def __init__(self, investigation_id: str) -> None:
        self.investigation_id = investigation_id
        self.nodes: list[DecisionProvenanceNode] = []
        self.edges: list[DecisionProvenanceEdge] = []
        self._node_ids: set[str] = set()

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        timestamp: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> DecisionProvenanceNode:
        if node_id not in self._node_ids:
            node = DecisionProvenanceNode(
                id=node_id,
                type=node_type,
                label=label,
                timestamp=timestamp,
                metadata=metadata or {},
            )
            self.nodes.append(node)
            self._node_ids.add(node_id)
            return node
        return next(n for n in self.nodes if n.id == node_id)

    def add_edge(self, source: str, target: str, relation: str) -> DecisionProvenanceEdge:
        edge = DecisionProvenanceEdge(source=source, target=target, relation=relation)
        self.edges.append(edge)
        return edge

    def to_mermaid(self) -> str:
        """Renders the provenance graph in Mermaid flowchart syntax."""
        lines = ["graph TD"]
        # Node styling classes
        style_map = {
            "observation": "fill:#e1f5fe,stroke:#0288d1",
            "hypothesis": "fill:#fff9c4,stroke:#fbc02d",
            "action": "fill:#f3e5f5,stroke:#8e24aa",
            "evidence": "fill:#e8f5e9,stroke:#388e3c",
            "falsification": "fill:#ffebee,stroke:#d32f2f",
            "decision": "fill:#e0f2f1,stroke:#00796b,stroke-width:2px",
            "state_transition": "fill:#eceff1,stroke:#607d8b",
        }

        for node in self.nodes:
            clean_label = node.label.replace('"', "'").replace("\n", " ")
            lines.append(f'    {node.id}["{clean_label}"]')

        for edge in self.edges:
            lines.append(f'    {edge.source} -->|"{edge.relation}"| {edge.target}')

        return "\n".join(lines)

    def to_contract(self) -> DecisionProvenanceGraphData:
        return DecisionProvenanceGraphData(
            nodes=self.nodes,
            edges=self.edges,
            mermaid_diagram=self.to_mermaid(),
        )

    def export_jsonl(self, filepath: str) -> None:
        """Exports nodes and edges as JSON Lines."""
        with open(filepath, "w", encoding="utf-8") as f:
            for node in self.nodes:
                f.write(json.dumps({"type": "node", **node.model_dump()}) + "\n")
            for edge in self.edges:
                f.write(json.dumps({"type": "edge", **edge.model_dump()}) + "\n")
