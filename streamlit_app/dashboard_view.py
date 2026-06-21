"""
Dashboard — mirrors frontend/src/pages/Dashboard.jsx
Sidebar: upload + document list. Main pane: chat with source citations.
"""
import streamlit as st

from api_client import (
    ApiError,
    list_documents,
    upload_document,
    delete_document,
    query,
    get_history,
)

STATUS_COLOR = {"ready": "🟢", "processing": "🟡", "failed": "🔴"}
FILE_ICON = {"pdf": "📄", "docx": "📝", "csv": "📊"}


def _load_documents(token: str):
    try:
        st.session_state.documents = list_documents(token)
    except ApiError as e:
        st.session_state.documents = []
        st.session_state.doc_load_error = str(e)


def _load_history(token: str):
    try:
        history = get_history(token)
        st.session_state.messages = [
            {"role": m["role"], "content": m["content"], "sources": m.get("sources") or []}
            for m in history
        ]
    except ApiError:
        st.session_state.messages = []


def render(user: dict, token: str, on_logout):
    # ---- One-time load per session, equivalent to Dashboard.jsx's
    # useEffect(() => { loadDocuments(); loadHistory(); }, [])
    if "documents" not in st.session_state:
        _load_documents(token)
    if "messages" not in st.session_state:
        _load_history(token)

    _render_sidebar(user, token, on_logout)
    _render_chat(token)


def _render_sidebar(user: dict, token: str, on_logout):
    with st.sidebar:
        header_col, btn_col = st.columns([3, 1])
        with header_col:
            st.markdown("### 🧠 DocuMind")
        with btn_col:
            if st.button("Logout", use_container_width=True):
                on_logout()

        st.caption(f"Hi, {user.get('username')} 👋")

        # ---- Upload ----
        uploaded_file = st.file_uploader(
            "Upload Document",
            type=["pdf", "docx", "csv"],
            label_visibility="collapsed",
            key="uploader",
        )
        st.caption("PDF, DOCX, or CSV")

        if uploaded_file is not None and st.session_state.get("last_uploaded") != uploaded_file.file_id:
            try:
                with st.spinner("⏳ Uploading..."):
                    upload_document(uploaded_file, token)
                st.session_state.last_uploaded = uploaded_file.file_id
                st.success("Uploaded! Processing in background.")
                _load_documents(token)
                st.rerun()
            except ApiError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Upload failed: {e}")

        st.divider()

        # ---- Document list ----
        docs = st.session_state.get("documents", [])
        st.markdown(f"**Documents ({len(docs)})**")

        if st.button("🔄 Refresh", use_container_width=True):
            _load_documents(token)
            st.rerun()

        if not docs:
            st.caption("No documents yet")

        for doc in docs:
            icon = FILE_ICON.get(doc["file_type"], "📁")
            status = doc["status"]
            status_dot = STATUS_COLOR.get(status, "⚪")
            meta = f"{status_dot} {status}"
            if status == "ready":
                meta += f" · {doc['chunk_count']} chunks"

            doc_col, del_col = st.columns([5, 1])
            with doc_col:
                st.markdown(f"{icon} **{doc['original_name']}**")
                st.caption(meta)
            with del_col:
                if st.button("🗑", key=f"del_{doc['id']}"):
                    try:
                        delete_document(doc["id"], token)
                        _load_documents(token)
                        st.rerun()
                    except ApiError as e:
                        st.error(str(e))


def _render_chat(token: str):
    st.markdown("## 💬 Ask anything")

    messages = st.session_state.get("messages", [])

    if not messages:
        st.info("Upload documents in the sidebar, then ask questions about them.")

    # ---- Render existing chat history ----
    for i, msg in enumerate(messages):
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(msg["content"])
            sources = msg.get("sources") or []
            if msg["role"] == "assistant" and sources:
                with st.expander(f"📎 Sources ({len(sources)})"):
                    for s in sources:
                        score = s.get("relevance_score", 0) * 100
                        page = s.get("page_number")
                        page_str = f" · p.{page}" if page is not None else ""
                        st.markdown(f"**{s.get('filename')}**{page_str} — `{score:.0f}%` relevance")
                        st.caption(f"\u201c{s.get('excerpt', '')}\u201d")

    # ---- Chat input, equivalent to handleQuery in Dashboard.jsx ----
    question = st.chat_input("Ask a question about your documents...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question, "sources": []})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    res = query(question, token)
                    answer = res["answer"]
                    sources = res.get("sources", [])
                except ApiError as e:
                    answer = f"Error: {e}"
                    sources = []
                except Exception as e:
                    answer = f"Error: could not reach the server ({e})"
                    sources = []

            st.markdown(answer)
            if sources:
                with st.expander(f"📎 Sources ({len(sources)})"):
                    for s in sources:
                        score = s.get("relevance_score", 0) * 100
                        page = s.get("page_number")
                        page_str = f" · p.{page}" if page is not None else ""
                        st.markdown(f"**{s.get('filename')}**{page_str} — `{score:.0f}%` relevance")
                        st.caption(f"\u201c{s.get('excerpt', '')}\u201d")

        st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
