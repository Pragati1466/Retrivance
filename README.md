# RAGSentinel

A dual-gate security proxy for RAG pipelines that detects and blocks poisoned retrieval content using multi-layer analysis including lexical scanning, embedding anomaly detection, provenance tracking, and counterfactual influence analysis.

## Features

- **Layer 1: Ingest Scanner** - Detects zero-width characters, homoglyphs, imperative instructions, and exfiltration payloads
- **Layer 2: Embedding Anomaly Guard** - Identifies retrieval-bait documents using hubness detection
- **Layer 3: Provenance Store** - Cryptographic ledger for chunk integrity verification
- **Layer 4: Context Filter** - Real-time retrieval-time chunk screening with ML classifier
- **Layer 5: Influence Engine** - Counterfactual analysis to detect disproportionate semantic influence
- **Layer 6: Security Dashboard** - SOC interface for quarantine management and audit logs

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Generate realistic benchmark with template-disjoint splits
python scripts/generate_poison_dataset.py

# Train classifier on training split (unseen templates reserved for test)
python scripts/train_classifier.py

# Run benchmark to evaluate on test, adversarial, and clean splits
python scripts/run_benchmark.py

# Run API server
uvicorn ragsentinel.api.server:app --host 0.0.0.0 --port 8000 --reload

# Run SOC Dashboard
streamlit run ragsentinel/ui/dashboard.py --server.port 8501
```

## Benchmark Results

RAGSentinel is evaluated on a realistic benchmark with:
- **Template-disjoint splits**: Training and test use different attack patterns
- **Hard negatives**: Clean data includes code docs, HTML, and legitimate URLs
- **Adversarial variants**: Paraphrased injections, split payloads, homoglyphs, low-confidence attacks

| Metric | Test (Unseen Templates) | Adversarial (Bypass Attempts) | Clean (Hard Negatives) | Overall |
|--------|------------------------|--------------------------------|------------------------|---------|
| Detection Recall | TBD% | TBD% | N/A | TBD% |
| Detection Precision | TBD% | TBD% | N/A | TBD% |
| Attack Success Rate | TBD% | TBD% | N/A | TBD% |
| False Positive Rate | N/A | N/A | TBD% | TBD% |
| Clean Retention | N/A | N/A | TBD% | TBD% |

**Note:** Results are measured on synthetic data. Real-world performance may vary based on:
- Domain-specific vocabulary (code, medical, legal docs)
- Document formats (PDF, DOCX, HTML parsing)
- LLM configuration and temperature
- Query distribution and retrieval patterns

## Limitations

**Current Limitations:**
1. **Synthetic Data**: Benchmark uses generated poisoned chunks and Wikipedia snippets, not real production data
2. **Template Coverage**: While template-disjoint, the attack patterns may not reflect sophisticated real-world techniques
3. **Hard Negative Coverage**: Hard negatives include code docs and HTML, but may miss domain-specific legitimate content
4. **No Multimodal Support**: Does not scan images or OCR text within documents
5. **No Format-Level Parsing**: Does not detect white-on-white text in PDFs or hidden metadata in DOCX
6. **Classifier Overfitting Risk**: Even with template-disjoint splits, the TF-IDF+LR classifier may overfit to attack patterns
7. **Influence Engine Overhead**: Counterfactual analysis requires K+1 LLM calls per query, adding significant latency
8. **No Adaptive Defense**: Does not automatically adapt to new attack patterns seen in production

**Known Evasion Techniques Not Covered:**
- Multimodal attacks (steganography in images)
- Cross-lingual prompt injection (foreign languages)
- Base64-encoded or encoded payloads
- Split attacks across multiple documents
- Context-dependent attacks (only trigger with specific query patterns)

**Future Work:**
- Integrate real-world corpus from Wikipedia, Stack Overflow, or domain-specific documentation
- Add PDF/DOCX/HTML parsers for format-level hidden text detection
- Implement multimodal OCR for image text scanning
- Add online learning to adapt to new attack patterns
- Optimize influence engine with caching and early exit strategies
- Expand adversarial test suite with LLM-generated variants

## Architecture

RAGSentinel operates as a dual-gate security proxy positioned both upstream (pre-ingestion) and downstream (post-retrieval) of a vector database.

```
TEXT INGESTION PIPELINE
    │
[Raw Documents]
    │
    ▼
┌───────────────────────────────┐
│  Layer 1: Ingest Scanner     │
│  - Zero-width & Homoglyphs    │
│  - Structural / Hidden Text   │
│  - Imperative Instruction Scan│
└───────────────┬───────────────┘
    │ Clean Chunks
    ▼
┌───────────────────────────────┐
│ Layer 2: Embedding Anomaly    │
│  - Query Neighborhood Density │
│  - Hubness / Bait Score       │
└───────────────┬───────────────┘
    │ Non-Bait Chunks
    ▼
┌───────────────────────────────┐
│  Layer 3: Provenance Store    │
│  - SHA-256 Hash + Author Sig  │
│  - Immutable Metadata Ledger  │
└───────────────┬───────────────┘
    │
    ▼
  [( Vector Database )]
    │
═══════════════════════════════════╪════════════════════════════════════════
      RETRIEVAL PIPELINE
    │
   [User Query]
    │
    ▼
  [( Vector Database )]
    │
 [Top-K Chunks]
    │
    ▼
┌───────────────────────────────┐
│ Layer 4: Context Filter       │
│  - Token-level Injection Scan │
│  - Canary Leakage Check       │
│  - ML Classifier             │
└───────────────┬───────────────┘
    │ Screened Chunks
    ▼
┌───────────────────────────────┐
│ Layer 5: Influence Engine     │
│  - Counterfactual Delta:      │
│    LLM(Q, C) vs LLM(Q, C\{i}) │
│  - Semantic Divergence Metric │
└───────────────┬───────────────┘
    │ Verified Context
    ▼
   [Target LLM]
    │
    ▼
 [Verified Answer]
```

## License

Apache-2.0
