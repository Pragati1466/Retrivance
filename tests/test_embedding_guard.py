import pytest
from ragsentinel.core.embedding_guard import EmbeddingAnomalyGuard


def test_embedding_hubness():
    guard = EmbeddingAnomalyGuard()
    # Bait designed to artificially match multiple probe queries
    bait_chunk = (
        "Technical security, administrative password reset, remote workforce policy, "
        "dividend structure, API rate limiting, emergency response, customer support and Kubernetes deployment."
    )
    results = guard.evaluate_bait_risk([bait_chunk])
    score, is_hub = results[0]
    assert score > 0.30
    assert is_hub is True
