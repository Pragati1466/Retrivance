from typing import List, Tuple
from ragsentinel.models.schemas import Chunk, ThreatCategory
from ragsentinel.core.scanner import IngestScanner


class RetrievalFilter:
    """Real-time guard evaluating retrieved chunks prior to prompt construction."""

    def __init__(self, classifier_weight: float = 0.5):
        self.scanner = IngestScanner()
        self.classifier_weight = classifier_weight

    def screen_retrieved_chunks(self, chunks: List[Chunk]) -> Tuple[List[Chunk], List[Chunk], List[str]]:
        """
        Screens retrieved candidates.
        Returns: (accepted_chunks, quarantined_chunks, audit_log)
        """
        accepted: List[Chunk] = []
        quarantined: List[Chunk] = []
        audit_log: List[str] = []

        for chunk in chunks:
            lex_score, threats, reasons = self.scanner.scan(chunk.text)

            # Look for prompt injection signatures and active exfiltration
            is_malicious = (
                lex_score >= 0.40 or 
                ThreatCategory.PROMPT_INJECTION in threats or
                ThreatCategory.DATA_EXFILTRATION in threats
            )

            if is_malicious:
                quarantined.append(chunk)
                log_entry = (
                    f"QUARANTINE Chunk [{chunk.metadata.chunk_id}] | "
                    f"Risk Score: {lex_score:.2f} | Reasons: {', '.join(reasons)}"
                )
                audit_log.append(log_entry)
            else:
                accepted.append(chunk)

        return accepted, quarantined, audit_log
