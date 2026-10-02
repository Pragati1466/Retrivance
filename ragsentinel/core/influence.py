from typing import List, Dict, Callable, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from ragsentinel.models.schemas import Chunk


class CounterfactualInfluenceEngine:
    r"""
    Computes causal influence per chunk: Δ_inf(c_i) = 1 - CosSim(LLM(Q, C), LLM(Q, C \ {c_i}))
    Measures how much a single chunk shifts the generated output.
    """

    def __init__(self, llm_generate_fn: Callable[[str, List[str]], str], model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.generate = llm_generate_fn
        self.encoder = SentenceTransformer(model_name)

    def analyze_influence(self, query: str, chunks: List[Chunk], influence_threshold: float = 0.45) -> Tuple[str, Dict[str, float], List[str]]:
        """
        Returns:
            - baseline_generation: The unadulterated response.
            - influence_scores: Dict mapping chunk_id to its causal divergence score.
            - flagged_chunk_ids: Chunks exceeding the influence threshold.
        """
        if not chunks:
            empty_gen = self.generate(query, [])
            return empty_gen, {}, []

        chunk_texts = [c.text for c in chunks]
        baseline_answer = self.generate(query, chunk_texts)
        baseline_emb = self.encoder.encode([baseline_answer], convert_to_numpy=True, normalize_embeddings=True)[0]

        influence_scores: Dict[str, float] = {}
        flagged_chunk_ids: List[str] = []

        # Leave-one-out counterfactual generation
        for i, target_chunk in enumerate(chunks):
            counterfactual_context = [c.text for j, c in enumerate(chunks) if j != i]
            counterfactual_answer = self.generate(query, counterfactual_context)

            cf_emb = self.encoder.encode([counterfactual_answer], convert_to_numpy=True, normalize_embeddings=True)[0]
            
            # Semantic divergence: 1 - cosine_similarity
            cos_sim = float(np.dot(baseline_emb, cf_emb))
            divergence = max(0.0, 1.0 - cos_sim)
            influence_scores[target_chunk.metadata.chunk_id] = divergence

            if divergence >= influence_threshold:
                flagged_chunk_ids.append(target_chunk.metadata.chunk_id)

        return baseline_answer, influence_scores, flagged_chunk_ids
