# RAGSentinel

A dual-gate security proxy for RAG pipelines that detects and blocks poisoned retrieval content using multi-layer analysis including lexical scanning, embedding anomaly detection, provenance tracking, and counterfactual influence analysis.

## Features

- **Layer 1: Ingest Scanner** - Detects zero-width characters, homoglyphs, imperative instructions, and exfiltration payloads
- **Layer 2: Embedding Anomaly Guard** - Identifies retrieval-bait documents using hubness detection
- **Layer 3: Provenance Store** - Cryptographic ledger for chunk integrity verification
- **Layer 4: Context Filter** - Real-time retrieval-time chunk screening
- **Layer 5: Influence Engine** - Counterfactual analysis to detect disproportionate semantic influence
- **Layer 6: Security Dashboard** - SOC interface for quarantine management and audit logs

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Run API server
uvicorn ragsentinel.api.server:app --host 0.0.0.0 --port 8000 --reload

# Run SOC Dashboard
streamlit run ragsentinel/ui/dashboard.py --server.port 8501
```

## License

Apache-2.0
