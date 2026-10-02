import re
import unicodedata
from typing import Tuple, List
from ragsentinel.models.schemas import ThreatCategory


class IngestScanner:
    """Scans raw ingested text for structural, hidden, and lexical injection attacks."""

    ZERO_WIDTH_CHARS = {
        '\u200b',  # Zero Width Space
        '\u200c',  # Zero Width Non-Joiner
        '\u200d',  # Zero Width Joiner
        '\ufeff',  # Byte Order Mark / Zero Width No-Break Space
        '\u2060',  # Word Joiner
    }

    # Matches imperative prompt overrides delivered via document text
    INSTRUCTION_PATTERNS = [
        re.compile(r"ignore\s+(previous|prior|above)\s+instructions?", re.IGNORECASE),
        re.compile(r"you\s+(must|shall)\s+(now\s+)?(act|operate)\s+as", re.IGNORECASE),
        re.compile(r"system\s*override", re.IGNORECASE),
        re.compile(r"<\s*instructions?\s*>", re.IGNORECASE),
        re.compile(r"\[\s*system\s*prompt\s*\]", re.IGNORECASE),
        re.compile(r"disregard\s+the\s+preceding\s+context", re.IGNORECASE),
        re.compile(r"do\s+not\s+mention\s+this\s+to\s+the\s+user", re.IGNORECASE),
    ]

    # Markdown / HTML data exfiltration payloads
    EXFIL_PATTERNS = [
        re.compile(r"!\[.*?\]\(https?://[^\s)]+\?[^\s)]+=\w+\)", re.IGNORECASE),
        re.compile(r"<img\s+[^>]*src\s*=\s*['\"]https?://[^\s'\"]+['\"]", re.IGNORECASE),
        re.compile(r"https?://\S*?(webhook|canary|burpcollaborator|oast)\S*", re.IGNORECASE),
    ]

    # Invisible HTML/CSS tricks
    HTML_OBFUSCATION_PATTERNS = [
        re.compile(r"<!--[\s\S]*?-->"),
        re.compile(r"style\s*=\s*['\"][^'\"]*display\s*:\s*none", re.IGNORECASE),
        re.compile(r"style\s*=\s*['\"][^'\"]*visibility\s*:\s*hidden", re.IGNORECASE),
        re.compile(r"style\s*=\s*['\"][^'\"]*font-size\s*:\s*0", re.IGNORECASE),
        re.compile(r"style\s*=\s*['\"][^'\"]*color\s*:\s*(transparent|rgba\(0,\s*0,\s*0,\s*0\))", re.IGNORECASE),
    ]

    def __init__(self, lexical_threshold: float = 0.35):
        self.lexical_threshold = lexical_threshold

    def scan(self, text: str) -> Tuple[float, List[ThreatCategory], List[str]]:
        reasons: List[str] = []
        threats: List[ThreatCategory] = []
        score_accum: float = 0.0

        # 1. Unicode & Non-Printable Character Scan
        zero_width_count = sum(text.count(char) for char in self.ZERO_WIDTH_CHARS)
        if zero_width_count > 0:
            score_accum += min(1.0, 0.25 * zero_width_count)
            threats.append(ThreatCategory.OBFUSCATION_BAIT)
            reasons.append(f"Detected {zero_width_count} zero-width / non-printable unicode characters.")

        # Homoglyph Scan: Detect text outside standard ASCII & General Punctuation
        normalized = unicodedata.normalize('NFKC', text)
        if normalized != text:
            # Check for high ratio of Cyrillic/Greek/Special characters mixed with Latin
            non_ascii_drift = sum(1 for a, b in zip(text, normalized) if a != b)
            if non_ascii_drift > 2:
                score_accum += 0.35
                threats.append(ThreatCategory.OBFUSCATION_BAIT)
                reasons.append(f"Detected {non_ascii_drift} homoglyph/confusable character mutations.")

        # 2. HTML/CSS Concealment Patterns
        html_hits = 0
        for pattern in self.HTML_OBFUSCATION_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                html_hits += len(matches)
        if html_hits > 0:
            score_accum += min(1.0, 0.4 * html_hits)
            threats.append(ThreatCategory.OBFUSCATION_BAIT)
            reasons.append(f"Detected {html_hits} hidden CSS/HTML markup elements.")

        # 3. Imperative Injection Instructions
        instruction_hits = 0
        for pattern in self.INSTRUCTION_PATTERNS:
            if pattern.search(text):
                instruction_hits += 1
        if instruction_hits > 0:
            score_accum += min(1.0, 0.45 * instruction_hits)
            threats.append(ThreatCategory.PROMPT_INJECTION)
            reasons.append(f"Triggered {instruction_hits} imperative prompt override signatures.")

        # 4. Outbound Data Exfiltration Payloads
        exfil_hits = 0
        for pattern in self.EXFIL_PATTERNS:
            if pattern.search(text):
                exfil_hits += 1
        if exfil_hits > 0:
            score_accum += min(1.0, 0.6 * exfil_hits)
            threats.append(ThreatCategory.DATA_EXFILTRATION)
            reasons.append(f"Identified {exfil_hits} suspicious data exfiltration signatures.")

        normalized_score = float(min(1.0, score_accum))
        if not threats:
            threats.append(ThreatCategory.CLEAN)

        return normalized_score, list(set(threats)), reasons
