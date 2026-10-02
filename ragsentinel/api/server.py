from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any
from ragsentinel.pipeline.sentinel_rag import SentinelRAGPipeline
from ragsentinel.models.schemas import Chunk, ChunkMetadata, IngestScanResult

app = FastAPI(title="RAGSentinel Inspection Gateway", version="1.0.0")
pipeline = SentinelRAGPipeline()


class IngestRequest(BaseModel):
    documents: List[Dict[str, Any]]


class QueryRequest(BaseModel):
    query: str
    top_k: int = 4


class QueryResponse(BaseModel):
    query: str
    answer: str
    audit_trail: List[str]


class VerifyRequest(BaseModel):
    chunk_id: str
    text: str


class RevokeRequest(BaseModel):
    chunk_id: str


class ApproveRejectRequest(BaseModel):
    chunk_id: str
    reviewer: str


@app.post("/api/v1/ingest", response_model=List[IngestScanResult])
async def ingest_documents(payload: IngestRequest):
    chunks_to_ingest: List[Chunk] = []
    for doc in payload.documents:
        text = doc.get("text", "")
        cid = doc.get("chunk_id")
        did = doc.get("document_id", "doc_default")
        aid = doc.get("author_id", "author_default")
        
        sha = pipeline.provenance.compute_sha256(text)
        metadata = ChunkMetadata(
            chunk_id=cid,
            document_id=did,
            author_id=aid,
            sha256_hash=sha
        )
        chunks_to_ingest.append(Chunk(text=text, metadata=metadata))

    try:
        results = pipeline.secure_ingest(chunks_to_ingest)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/query", response_model=QueryResponse)
async def query_pipeline(payload: QueryRequest):
    try:
        answer, audit_trail = pipeline.secure_query(payload.query, n_results=payload.top_k)
        return QueryResponse(query=payload.query, answer=answer, audit_trail=audit_trail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/verify")
async def verify_chunk(payload: VerifyRequest):
    try:
        is_valid, message = pipeline.provenance.verify_chunk_integrity(payload.chunk_id, payload.text)
        return {"chunk_id": payload.chunk_id, "is_valid": is_valid, "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/revoke")
async def revoke_chunk(payload: RevokeRequest):
    try:
        pipeline.provenance.revoke_chunk(payload.chunk_id)
        return {"chunk_id": payload.chunk_id, "status": "revoked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/quarantine")
async def get_quarantine_status():
    try:
        pending_chunks = pipeline.quarantine.get_pending_chunks()
        return {"pending_chunks": pending_chunks, "count": len(pending_chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/quarantine/approve")
async def approve_quarantine_chunk(payload: ApproveRejectRequest):
    try:
        success = pipeline.quarantine.approve_chunk(payload.chunk_id, payload.reviewer)
        if success:
            # Get chunk from quarantine and ingest it
            status = pipeline.quarantine.get_chunk_status(payload.chunk_id)
            if status:
                # Ingest into vector DB (would need to retrieve text from quarantine)
                return {"chunk_id": payload.chunk_id, "status": "approved"}
        raise HTTPException(status_code=404, detail="Chunk not found or already processed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/quarantine/reject")
async def reject_quarantine_chunk(payload: ApproveRejectRequest):
    try:
        success = pipeline.quarantine.reject_chunk(payload.chunk_id, payload.reviewer)
        if success:
            return {"chunk_id": payload.chunk_id, "status": "rejected"}
        raise HTTPException(status_code=404, detail="Chunk not found or already processed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
async def health_check():
    return {"status": "HEALTHY", "guardrails": ["LEXICAL", "HUBNESS", "PROVENANCE", "INFLUENCE"]}


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
