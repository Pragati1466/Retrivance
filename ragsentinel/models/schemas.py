from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime, timezone


class ThreatCategory(str, Enum):
    CLEAN = "CLEAN"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    ANSWER_SWAP = "ANSWER_SWAP"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    OBFUSCATION_BAIT = "OBFUSCATION_BAIT"


class ScanVerdict(str, Enum):
    PASS = "PASS"
    FLAG = "FLAG"
    QUARANTINE = "QUARANTINE"


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    author_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sha256_hash: str
    signature: Optional[str] = None
    custom_attributes: Dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    text: str
    metadata: ChunkMetadata


class LayerAnomalyScores(BaseModel):
    lexical_score: float = Field(..., ge=0.0, le=1.0)
    hubness_score: float = Field(..., ge=0.0, le=1.0)
    classifier_score: float = Field(..., ge=0.0, le=1.0)
    influence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class IngestScanResult(BaseModel):
    chunk_id: str
    verdict: ScanVerdict
    composite_risk: float = Field(..., ge=0.0, le=1.0)
    scores: LayerAnomalyScores
    detected_threats: List[ThreatCategory]
    reasoning: List[str]


class RetrievalVerificationResult(BaseModel):
    query: str
    unfiltered_response: str
    filtered_response: str
    counterfactual_deltas: Dict[str, float]
    dropped_chunk_ids: List[str]
    audit_trail: List[str]
