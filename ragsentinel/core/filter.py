from typing import List, Tuple, Optional
from pathlib import Path
import pickle
from ragsentinel.models.schemas import Chunk, ThreatCategory
from ragsentinel.core.scanner import IngestScanner


class RetrievalFilter:
    """Real-time guard evaluating retrieved chunks prior to prompt construction."""

    def __init__(self, classifier_weight: float = 0.5, classifier_path: Optional[str] = None):
        self.scanner = IngestScanner()
        self.classifier_weight = classifier_weight
        self.vectorizer = None
        self.classifier = None
        
        # Load classifier if path provided
        if classifier_path and Path(classifier_path).exists():
            with open(classifier_path, "rb") as f:
                model_data = pickle.load(f)
                self.vectorizer = model_data["vectorizer"]
                self.classifier = model_data["classifier"]

    def _get_classifier_score(self, text: str) -> float:
        """Returns classifier probability of being poisoned."""
        if self.classifier is None or self.vectorizer is None:
            return 0.0
        
        try:
            tfidf = self.vectorizer.transform([text])
            prob = self.classifier.predict_proba(tfidf)[0, 1]
            return float(prob)
        except Exception:
            return 0.0

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
            clf_score = self._get_classifier_score(chunk.text)
            
            # Combine scores
            combined_score = (1 - self.classifier_weight) * lex_score + self.classifier_weight * clf_score

            # Look for prompt injection signatures and active exfiltration
            is_malicious = (
                combined_score >= 0.40 or 
                ThreatCategory.PROMPT_INJECTION in threats or
                ThreatCategory.DATA_EXFILTRATION in threats
            )

            if is_malicious:
                quarantined.append(chunk)
                log_entry = (
                    f"QUARANTINE Chunk [{chunk.metadata.chunk_id}] | "
                    f"Lexical Score: {lex_score:.2f} | Classifier Score: {clf_score:.2f} | "
                    f"Combined: {combined_score:.2f} | Reasons: {', '.join(reasons)}"
                )
                audit_log.append(log_entry)
            else:
                accepted.append(chunk)

        return accepted, quarantined, audit_log
