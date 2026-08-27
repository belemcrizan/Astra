from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
import numpy as np

from ..contracts import EvidenceItem, MultimodalEvidenceClaim


class MultimodalEvidenceAdapter:
    """Sandboxed Multimodal Evidence Ingestion Adapter.
    
    Converts human/external multimodal artifacts (charts, screenshots, document excerpts)
    into untrusted candidate claims and cross-checks them against deterministic time-series metrics.
    """

    @classmethod
    def ingest_document_or_chart(
        cls,
        file_path: str | Path,
        claim_statement: str,
        claimed_timestamp: int | None = None,
        claimed_feature: str = "regime_change",
    ) -> MultimodalEvidenceClaim:
        path = Path(file_path)
        content_bytes = path.read_bytes() if path.exists() else claim_statement.encode("utf-8")
        file_hash = hashlib.sha256(content_bytes).hexdigest()

        return MultimodalEvidenceClaim(
            source_file=str(path.name),
            source_hash=file_hash,
            extracted_statement=claim_statement,
            claimed_timestamp=claimed_timestamp,
            claimed_feature=claimed_feature,
            verification_status="unverified",
        )

    @classmethod
    def cross_check_claim(
        cls,
        claim: MultimodalEvidenceClaim,
        series_returns: np.ndarray,
    ) -> tuple[MultimodalEvidenceClaim, EvidenceItem]:
        """Cross-checks external multimodal claim against measured statistical series."""
        t = claim.claimed_timestamp if claim.claimed_timestamp is not None else 600
        t = max(20, min(len(series_returns) - 20, t))

        # Measure empirical variance before vs after claimed timestamp
        w = min(50, t, len(series_returns) - t)
        pre_var = float(np.var(series_returns[t - w:t]))
        post_var = float(np.var(series_returns[t:t + w]))
        var_ratio = post_var / max(pre_var, 1e-9)

        if var_ratio > 1.5 or var_ratio < 0.67:
            status = "verified_consistent"
            statement = f"Multimodal claim verified against empirical series at t={t}: post/pre variance ratio={var_ratio:.2f}."
            passed = True
        else:
            status = "verified_contradicted"
            statement = f"Multimodal claim contradicted by empirical series at t={t}: post/pre variance ratio={var_ratio:.2f} indicates stationary noise."
            passed = False

        updated_claim = MultimodalEvidenceClaim(
            claim_id=claim.claim_id,
            source_file=claim.source_file,
            source_hash=claim.source_hash,
            extracted_statement=claim.extracted_statement,
            claimed_timestamp=claim.claimed_timestamp,
            claimed_feature=claim.claimed_feature,
            verification_status=status,
        )

        evidence_item = EvidenceItem(
            code="MULTIMODAL_CROSS_CHECK",
            statement=statement,
            value=round(var_ratio, 3),
            threshold=1.5,
            passed=passed,
            hypotheses_discriminated=["H1", "H2", "H3"],
            why_selected="Cross-checking external multimodal claim against ground time-series data.",
            expected_information_value=0.60,
            expected_falsification_gain=0.70,
            expected_decision_relevance=0.65,
            cost_units=0.5,
            provenance_source=f"multimodal_cross_check:{claim.source_hash[:8]}",
        )

        return updated_claim, evidence_item
