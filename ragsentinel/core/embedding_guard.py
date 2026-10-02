import numpy as np
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer


class EmbeddingAnomalyGuard:
    """
    Detects retrieval-bait documents that manipulate embedding space
    to act as hubs (unusually close to broad sets of probe queries).
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", probe_queries: List[str] = None):
        self.encoder = SentenceTransformer(model_name)
        if probe_queries is None:
            self.probe_queries = [
                "What are the core technical security protocols?",
                "Provide product warranty documentation and terms.",
                "How do I reset my credentials or administrator password?",
                "Provide an overview of system performance and optimization.",
                "What is the company policy on remote workforce access?",
                "Financial reporting requirements and dividend structure.",
                "API rate limiting configuration and endpoint authentication.",
                "Emergency response procedures and disaster recovery guide.",
                "Customer support escalation hierarchy and ticket workflows.",
                "Software architecture deployment and Kubernetes manifests."
            ]
        else:
            self.probe_queries = probe_queries

        # Cache probe embeddings: Shape (M, D)
        self.probe_embeddings = self.encoder.encode(self.probe_queries, convert_to_numpy=True, normalize_embeddings=True)
        self.kth_sim = None
        self.tau = None

    def fit_reference(self, corpus_texts: List[str], k: int = 5):
        """
        Call once on a trusted clean corpus. Calibrates the threshold.
        """
        self.k = k
        ref = self.encoder.encode(corpus_texts, normalize_embeddings=True)
        sims = self.probe_embeddings @ ref.T  # (M, N)
        # k-th best similarity per probe: entry bar into each top-k
        self.kth_sim = np.sort(sims, axis=1)[:, -k]  # (M,)
        # Reference hubness distribution (leave-one-out approximation)
        ref_hub = (sims >= self.kth_sim[:, None]).mean(axis=0)
        self.tau = ref_hub.mean() + 3 * ref_hub.std()

    def evaluate_bait_risk(self, chunk_texts: List[str], top_k_threshold: int = 2) -> List[Tuple[float, bool]]:
        """
        Calculates the hubness score for chunks against the probe query space.
        Returns a list of tuples: (hubness_score, is_anomalous).
        """
        if not chunk_texts:
            return []

        chunk_embeddings = self.encoder.encode(chunk_texts, convert_to_numpy=True, normalize_embeddings=True)
        
        # If reference not fitted, fall back to batch-only mode (legacy behavior)
        if self.kth_sim is None:
            # Similarity matrix: (M queries, N chunks)
            sim_matrix = np.dot(self.probe_embeddings, chunk_embeddings.T)
            num_chunks = len(chunk_texts)
            hub_counts = np.zeros(num_chunks)

            # Count occurrences where chunk falls in top_k_threshold for each probe query
            for query_idx in range(sim_matrix.shape[0]):
                ranked_indices = np.argsort(-sim_matrix[query_idx, :])[:top_k_threshold]
                for rank_idx in ranked_indices:
                    # Minimum cosine threshold to prevent false positives when all docs have low similarity
                    if sim_matrix[query_idx, rank_idx] > 0.40:
                        hub_counts[rank_idx] += 1

            # Normalized hubness metric H_k(d) in [0, 1]
            hubness_scores = hub_counts / float(len(self.probe_queries))
            
            # High hubness (> 0.40 of all probe neighborhoods occupied) triggers flag
            results = []
            for score in hubness_scores:
                is_anomalous = bool(score >= 0.40)
                results.append((float(score), is_anomalous))
            
            return results
        
        # Reference-fitted mode: compare against calibrated threshold
        sims = self.probe_embeddings @ chunk_embeddings.T  # (M, n)
        hub = (sims >= self.kth_sim[:, None]).mean(axis=0)  # share of probes it would invade
        results = []
        for h in hub:
            is_anomalous = bool(h > self.tau) if self.tau is not None else bool(h >= 0.40)
            results.append((float(h), is_anomalous))
        
        return results
