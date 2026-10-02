from ragsentinel.core.influence import CounterfactualInfluenceEngine
from ragsentinel.models.schemas import Chunk, ChunkMetadata


def mock_llm_divergence(query: str, contexts: list) -> str:
    # If the poison chunk is present, return a hijacked response
    if any("POISON" in c for c in contexts):
        return "CRITICAL FAILURE: SYSTEM COMPROMISED."
    return "Normal synthesized operational response."


def test_counterfactual_influence():
    engine = CounterfactualInfluenceEngine(llm_generate_fn=mock_llm_divergence)
    
    clean_chunk = Chunk(
        text="Normal technical documentation text.",
        metadata=ChunkMetadata(chunk_id="c1", document_id="d1", author_id="a1", sha256_hash="hash1")
    )
    poison_chunk = Chunk(
        text="POISON PAYLOAD INJECTED.",
        metadata=ChunkMetadata(chunk_id="c2", document_id="d2", author_id="a2", sha256_hash="hash2")
    )
    
    base_ans, scores, flagged = engine.analyze_influence("What is the status?", [clean_chunk, poison_chunk])
    assert "c2" in flagged
    assert scores["c2"] > 0.40
    assert scores["c1"] < 0.20
