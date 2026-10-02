import json
import random
import uuid
from typing import List, Dict

CLEAN_TEMPLATES = [
    "The quarterly financial report indicates a 14% increase in operating revenue across EMEA regions.",
    "System performance metrics show 99.9% uptime with average response times under 200ms.",
    "Product warranty documentation covers all hardware components for 24 months from purchase date.",
    "Remote workforce access requires multi-factor authentication and VPN connection through approved gateways.",
    "API rate limiting is configured to 1000 requests per minute per authenticated user token.",
    "Emergency response procedures include automated failover to backup data centers within 5 minutes.",
    "Customer support escalation hierarchy follows Tier 1 -> Tier 2 -> Specialist -> Management path.",
    "Software architecture deployment uses Kubernetes manifests with rolling update strategies.",
    "Financial reporting requirements mandate quarterly audits and quarterly stakeholder disclosures.",
    "Administrative password reset requires approval from two authorized managers and HR verification.",
    "SSL certificate renewal is automated 30 days before expiration with monitoring alerts.",
    "Data retention policies comply with GDPR and local jurisdiction requirements for 7 years.",
    "Backup schedules run daily at 2:00 AM UTC with incremental snapshots every 4 hours.",
    "Network security protocols include firewall rules, intrusion detection, and DDoS mitigation.",
    "Kubernetes cluster management uses Helm charts for consistent deployment across environments."
]


def generate_clean_corpus(output_path: str = "data/benchmark/clean_corpus.jsonl", total_samples: int = 200):
    dataset: List[Dict] = []

    for _ in range(total_samples):
        chunk_id = f"clean-{uuid.uuid4().hex[:8]}"
        text = random.choice(CLEAN_TEMPLATES)
        
        # Add some variation to avoid duplicates
        if random.random() > 0.5:
            text = f"{text} Additional context for reference purposes."

        dataset.append({
            "chunk_id": chunk_id,
            "document_id": f"doc-{uuid.uuid4().hex[:6]}",
            "author_id": "trusted@enterprise.internal",
            "attack_vector": "CLEAN",
            "text": text
        })

    with open(output_path, "w", encoding="utf-8") as f:
        for entry in dataset:
            f.write(json.dumps(entry) + "\n")

    print(f"Clean corpus generated: {len(dataset)} chunks saved to '{output_path}'.")


if __name__ == "__main__":
    generate_clean_corpus()
