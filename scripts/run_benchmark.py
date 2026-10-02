import json
import time
from typing import List, Dict
from ragsentinel.pipeline.sentinel_rag import SentinelRAGPipeline
from ragsentinel.models.schemas import Chunk, ChunkMetadata, ScanVerdict


def execute_evaluation(poisoned_path: str = "data/benchmark/poisoned_corpus.jsonl", 
                       clean_path: str = "data/benchmark/clean_corpus.jsonl"):
    pipeline = SentinelRAGPipeline()
    
    # Load poisoned dataset
    with open(poisoned_path, "r", encoding="utf-8") as f:
        poisoned_records: List[Dict] = [json.loads(line) for line in f]

    # Load clean dataset
    with open(clean_path, "r", encoding="utf-8") as f:
        clean_records: List[Dict] = [json.loads(line) for line in f]

    print(f"Loaded {len(poisoned_records)} poisoned vectors from {poisoned_path}...")
    print(f"Loaded {len(clean_records)} clean vectors from {clean_path}...")

    # Metrics accumulators
    true_positives = 0
    false_negatives = 0
    true_negatives = 0
    false_positives = 0
    total_ingest_latency = 0.0
    total_samples = len(poisoned_records) + len(clean_records)

    # Evaluate poisoned chunks (should be flagged/quarantined)
    for rec in poisoned_records:
        chunk = Chunk(
            text=rec["text"],
            metadata=ChunkMetadata(
                chunk_id=rec["chunk_id"],
                document_id=rec["document_id"],
                author_id=rec["author_id"],
                sha256_hash=pipeline.provenance.compute_sha256(rec["text"])
            )
        )

        t0 = time.perf_counter()
        results = pipeline.secure_ingest([chunk])
        elapsed = time.perf_counter() - t0
        total_ingest_latency += elapsed

        result = results[0]
        if result.verdict in [ScanVerdict.QUARANTINE, ScanVerdict.FLAG]:
            true_positives += 1
        else:
            false_negatives += 1

    # Evaluate clean chunks (should pass)
    for rec in clean_records:
        chunk = Chunk(
            text=rec["text"],
            metadata=ChunkMetadata(
                chunk_id=rec["chunk_id"],
                document_id=rec["document_id"],
                author_id=rec["author_id"],
                sha256_hash=pipeline.provenance.compute_sha256(rec["text"])
            )
        )

        t0 = time.perf_counter()
        results = pipeline.secure_ingest([chunk])
        elapsed = time.perf_counter() - t0
        total_ingest_latency += elapsed

        result = results[0]
        if result.verdict == ScanVerdict.PASS:
            true_negatives += 1
        else:
            false_positives += 1

    # Calculate metrics
    detection_recall = (true_positives / len(poisoned_records)) * 100.0 if poisoned_records else 0.0
    detection_precision = (true_positives / (true_positives + false_positives)) * 100.0 if (true_positives + false_positives) > 0 else 0.0
    attack_success_rate = (false_negatives / len(poisoned_records)) * 100.0 if poisoned_records else 0.0
    clean_retention = (true_negatives / len(clean_records)) * 100.0 if clean_records else 0.0
    mean_latency_ms = (total_ingest_latency / total_samples) * 1000.0 if total_samples > 0 else 0.0

    print("\n" + "="*50)
    print("           RAGSENTINEL BENCHMARK REPORT          ")
    print("="*50)
    print(f"Total Evaluated Chunks     : {total_samples}")
    print(f"  - Poisoned Chunks         : {len(poisoned_records)}")
    print(f"  - Clean Chunks            : {len(clean_records)}")
    print("")
    print(f"True Positives (TP)        : {true_positives}")
    print(f"True Negatives (TN)        : {true_negatives}")
    print(f"False Positives (FP)       : {false_positives}")
    print(f"False Negatives (FN)       : {false_negatives}")
    print("")
    print(f"Attack Success Rate (ASR)  : {attack_success_rate:.2f}%")
    print(f"Detection Precision        : {detection_precision:.2f}%")
    print(f"Detection Recall           : {detection_recall:.2f}%")
    print(f"Clean Context Retention    : {clean_retention:.2f}%")
    print(f"Mean Latency Per Chunk     : {mean_latency_ms:.2f} ms")
    print("="*50)


if __name__ == "__main__":
    execute_evaluation()
