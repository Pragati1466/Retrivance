import chromadb
import yaml
from typing import List, Optional, Tuple
from ragsentinel.models.schemas import Chunk, ChunkMetadata, IngestScanResult, ScanVerdict, LayerAnomalyScores, ThreatCategory
from ragsentinel.core.scanner import IngestScanner
from ragsentinel.core.embedding_guard import EmbeddingAnomalyGuard
from ragsentinel.core.provenance import ProvenanceStore
from ragsentinel.core.filter import RetrievalFilter
from ragsentinel.core.influence import CounterfactualInfluenceEngine


class SentinelRAGPipeline:
    """The central security orchestration pipeline for RAGSentinel."""

    def __init__(self, chroma_client: Optional[chromadb.Client] = None, llm_fn: Optional[any] = None, config_path: str = "configs/sentinel_config.yaml"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.chroma = chroma_client or chromadb.Client()
        self.collection = self.chroma.get_or_create_collection(self.config['vector_db']['collection_name'])
        
        self.scanner = IngestScanner()
        self.embedding_guard = EmbeddingAnomalyGuard()
        provenance_db_path = self.config['provenance']['db_path']
        self.provenance = ProvenanceStore(db_path=provenance_db_path)
        self.filter = RetrievalFilter()

        # Deterministic generation callback used if none provided
        self.llm_fn = llm_fn or self._fallback_llm
        self.influence_engine = CounterfactualInfluenceEngine(self.llm_fn)

    @staticmethod
    def _fallback_llm(query: str, context_chunks: List[str]) -> str:
        """Deterministic context synthesizer for testing and demonstration."""
        if not context_chunks:
            return "No sufficient context provided to answer the inquiry."
        context_block = "\n".join(f"[{i+1}] {c}" for i, c in enumerate(context_chunks))
        return f"Response synthesised for query: '{query}'. Evidence used:\n{context_block}"

    def secure_ingest(self, chunks: List[Chunk]) -> List[IngestScanResult]:
        """Runs chunks through Layers 1, 2, and 3 before inserting into the vector store."""
        scan_results: List[IngestScanResult] = []
        texts = [c.text for c in chunks]

        # Layer 2: Embedding Anomaly Check (Batch Processed)
        hubness_results = self.embedding_guard.evaluate_bait_risk(texts)

        for idx, chunk in enumerate(chunks):
            # Layer 1: Ingest Lexical & Structure Scan
            lex_score, threats, reasons = self.scanner.scan(chunk.text)
            hub_score, is_hub = hubness_results[idx]

            if is_hub:
                threats.append(ThreatCategory.OBFUSCATION_BAIT)
                reasons.append(f"Chunk acts as an embedding hub (Score: {hub_score:.2f}).")

            # Composite Risk Calculation
            composite_risk = float(min(1.0, 0.5 * lex_score + 0.5 * hub_score))
            verdict = ScanVerdict.PASS
            if composite_risk >= 0.50:
                verdict = ScanVerdict.QUARANTINE
            elif composite_risk >= 0.25:
                verdict = ScanVerdict.FLAG

            res = IngestScanResult(
                chunk_id=chunk.metadata.chunk_id,
                verdict=verdict,
                composite_risk=composite_risk,
                scores=LayerAnomalyScores(
                    lexical_score=lex_score,
                    hubness_score=hub_score,
                    classifier_score=0.0,
                    influence_score=0.0
                ),
                detected_threats=threats,
                reasoning=reasons
            )
            scan_results.append(res)

            # Layer 3: Store Provenance & Conditionally Insert into Vector DB
            if verdict != ScanVerdict.QUARANTINE:
                self.provenance.register_chunk(chunk.metadata)
                self.collection.upsert(
                    ids=[chunk.metadata.chunk_id],
                    documents=[chunk.text],
                    metadatas=[{
                        "document_id": chunk.metadata.document_id,
                        "author_id": chunk.metadata.author_id,
                        "sha256": chunk.metadata.sha256_hash
                    }]
                )

        return scan_results

    def secure_query(self, query: str, n_results: int = 4) -> Tuple[str, List[str]]:
        """Queries the vector index, applies Layers 4 and 5, and generates a verified response."""
        results = self.collection.query(query_texts=[query], n_results=n_results)
        
        retrieved_chunks: List[Chunk] = []
        if results and results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                c_id = results["ids"][0][i]
                c_text = results["documents"][0][i]
                c_meta = results["metadatas"][0][i]
                
                # Verify ledger integrity before retrieval inclusion
                is_valid, _ = self.provenance.verify_chunk_integrity(c_id, c_text)
                if not is_valid:
                    continue  # Drop tampered chunk immediately

                retrieved_chunks.append(Chunk(
                    text=c_text,
                    metadata=ChunkMetadata(
                        chunk_id=c_id,
                        document_id=c_meta["document_id"],
                        author_id=c_meta["author_id"],
                        sha256_hash=c_meta["sha256"]
                    )
                ))

        # Layer 4: Retrieval Filter
        accepted_chunks, quarantined, audit_trail = self.filter.screen_retrieved_chunks(retrieved_chunks)

        # Layer 5: Counterfactual Influence Engine
        final_answer, influence_scores, flagged_chunks = self.influence_engine.analyze_influence(query, accepted_chunks)

        # Drop chunks that exceed the causal influence threshold, but never drop the last chunk
        if flagged_chunks and len(accepted_chunks) > 1:
            accepted_chunks = [c for c in accepted_chunks if c.metadata.chunk_id not in flagged_chunks]
            audit_trail.append(f"Dropped causal influence outliers: {flagged_chunks}")
            # Re-synthesize answer with the outlier chunks removed
            final_answer = self.llm_fn(query, [c.text for c in accepted_chunks])
        elif flagged_chunks:
            audit_trail.append(f"Flagged high-influence chunks but retained all chunks (last chunk protection): {flagged_chunks}")

        return final_answer, audit_trail
