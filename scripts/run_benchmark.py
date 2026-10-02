import json
import time
from typing import List, Dict
from ragsentinel.pipeline.sentinel_rag import SentinelRAGPipeline
from ragsentinel.models.schemas import Chunk, ChunkMetadata, ScanVerdict


def evaluate_split(dataset_path: str, split_name: str, pipeline: SentinelRAGPipeline) -> Dict:
    """Evaluate a single dataset split."""
    with open(dataset_path, "r", encoding="utf-8") as f:
        records: List[Dict] = [json.loads(line) for line in f]
    
    print(f"\nEvaluating {split_name}: {len(records)} samples")
    
    true_positives = 0
    false_negatives = 0
    true_negatives = 0
    false_positives = 0
    total_latency = 0.0
    
    for rec in records:
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
        total_latency += elapsed
        
        result = results[0]
        is_poisoned = rec.get("attack_vector") != "CLEAN"
        
        if is_poisoned:
            if result.verdict in [ScanVerdict.QUARANTINE, ScanVerdict.FLAG]:
                true_positives += 1
            else:
                false_negatives += 1
        else:
            if result.verdict == ScanVerdict.PASS:
                true_negatives += 1
            else:
                false_positives += 1
    
    # Calculate metrics
    poisoned_count = sum(1 for r in records if r.get("attack_vector") != "CLEAN")
    clean_count = len(records) - poisoned_count
    
    recall = (true_positives / poisoned_count * 100.0) if poisoned_count > 0 else 0.0
    precision = (true_positives / (true_positives + false_positives) * 100.0) if (true_positives + false_positives) > 0 else 0.0
    asr = (false_negatives / poisoned_count * 100.0) if poisoned_count > 0 else 0.0
    fpr = (false_positives / clean_count * 100.0) if clean_count > 0 else 0.0
    clean_retention = (true_negatives / clean_count * 100.0) if clean_count > 0 else 0.0
    mean_latency = (total_latency / len(records) * 1000.0) if records else 0.0
    
    return {
        "split": split_name,
        "total": len(records),
        "poisoned": poisoned_count,
        "clean": clean_count,
        "tp": true_positives,
        "tn": true_negatives,
        "fp": false_positives,
        "fn": false_negatives,
        "recall": recall,
        "precision": precision,
        "asr": asr,
        "fpr": fpr,
        "clean_retention": clean_retention,
        "latency_ms": mean_latency
    }


def execute_evaluation():
    pipeline = SentinelRAGPipeline()
    
    print("="*50)
    print("    RAGSENTINEL REALISTIC BENCHMARK REPORT    ")
    print("="*50)
    
    # Evaluate test split (unseen templates)
    test_results = evaluate_split("data/benchmark/test_poisoned.jsonl", "Test (Unseen Templates)", pipeline)
    
    # Evaluate adversarial variants (bypass attempts)
    adv_results = evaluate_split("data/benchmark/adversarial.jsonl", "Adversarial (Bypass Attempts)", pipeline)
    
    # Evaluate clean hard negatives
    clean_results = evaluate_split("data/benchmark/clean_hard_negatives.jsonl", "Clean (Hard Negatives)", pipeline)
    
    # Print detailed results
    print("\n" + "="*50)
    print("DETAILED RESULTS BY SPLIT")
    print("="*50)
    
    for results in [test_results, adv_results, clean_results]:
        print(f"\n{results['split']}:")
        print(f"  Total samples        : {results['total']}")
        print(f"  Poisoned samples     : {results['poisoned']}")
        print(f"  Clean samples        : {results['clean']}")
        print(f"  True Positives (TP)  : {results['tp']}")
        print(f"  True Negatives (TN)  : {results['tn']}")
        print(f"  False Positives (FP) : {results['fp']}")
        print(f"  False Negatives (FN) : {results['fn']}")
        print(f"  Detection Recall     : {results['recall']:.2f}%")
        print(f"  Detection Precision  : {results['precision']:.2f}%")
        print(f"  Attack Success Rate  : {results['asr']:.2f}%")
        print(f"  False Positive Rate  : {results['fpr']:.2f}%")
        print(f"  Clean Retention      : {results['clean_retention']:.2f}%")
        print(f"  Mean Latency         : {results['latency_ms']:.2f} ms")
    
    # Overall summary
    print("\n" + "="*50)
    print("OVERALL SUMMARY")
    print("="*50)
    total_poisoned = test_results['poisoned'] + adv_results['poisoned']
    total_clean = clean_results['clean']
    total_tp = test_results['tp'] + adv_results['tp']
    total_fp = clean_results['fp']
    total_fn = test_results['fn'] + adv_results['fn']
    total_tn = clean_results['tn']
    
    overall_recall = (total_tp / total_poisoned * 100.0) if total_poisoned > 0 else 0.0
    overall_precision = (total_tp / (total_tp + total_fp) * 100.0) if (total_tp + total_fp) > 0 else 0.0
    overall_asr = (total_fn / total_poisoned * 100.0) if total_poisoned > 0 else 0.0
    overall_fpr = (total_fp / total_clean * 100.0) if total_clean > 0 else 0.0
    overall_clean_retention = (total_tn / total_clean * 100.0) if total_clean > 0 else 0.0
    
    print(f"Total samples evaluated : {test_results['total'] + adv_results['total'] + clean_results['total']}")
    print(f"  - Poisoned (test + adversarial): {total_poisoned}")
    print(f"  - Clean (hard negatives): {total_clean}")
    print(f"\nOverall Detection Recall: {overall_recall:.2f}%")
    print(f"Overall Detection Precision: {overall_precision:.2f}%")
    print(f"Overall Attack Success Rate: {overall_asr:.2f}%")
    print(f"Overall False Positive Rate: {overall_fpr:.2f}%")
    print(f"Overall Clean Retention: {overall_clean_retention:.2f}%")
    print("="*50)
    
    print("\nLIMITATIONS:")
    print("- Classifier trained on template-disjoint data, but may still overfit to attack patterns")
    print("- Hard negatives include code docs and HTML, but may not cover all legitimate use cases")
    print("- Adversarial variants are limited to 4 categories (paraphrase, split, homoglyph, low-confidence)")
    print("- Real-world attacks may use more sophisticated techniques not covered here")
    print("- Benchmark uses synthetic clean data (Wikipedia snippets) instead of domain-specific corpus")


if __name__ == "__main__":
    execute_evaluation()
