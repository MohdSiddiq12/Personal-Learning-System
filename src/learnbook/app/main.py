"""Local-only Streamlit interface for PDF ingestion and page browsing."""

import hashlib

import streamlit as st

from learnbook.app.view_models import (
    export_text,
    page_preview,
    search_pages,
    summary_rows,
)
from learnbook.config import Settings
from learnbook.core.ingestion import extract_pdf
from learnbook.core.ingestion.errors import IngestionError
from learnbook.core.ingestion.models import ExtractedDocument


def _record_upload_change() -> None:
    st.session_state["upload_event"] = st.session_state.get("upload_event", 0) + 1


def _initialize_session_state() -> None:
    st.session_state.setdefault("upload_event", 0)
    st.session_state.setdefault("handled_upload_event", None)
    st.session_state.setdefault("seen_upload_hashes", set())
    st.session_state.setdefault("extracted_documents", {})
    st.session_state.setdefault("active_upload_hash", None)
    st.session_state.setdefault("duplicate_upload_hash", None)
    st.session_state.setdefault("page_number", 1)


def _render_document_summary(document: ExtractedDocument) -> None:
    for label, value in summary_rows(document):
        st.text(f"{label}: {value}")


def _render_page_browser(document: ExtractedDocument, file_hash: str) -> None:
    query = st.text_input("Search text", key="search_query")
    matching_pages = search_pages(document, query)
    if query:
        if matching_pages:
            selected_page = st.selectbox(
                "Matching page",
                options=matching_pages,
                format_func=lambda number: f"Page {number}",
                key=f"search-result-{file_hash[:12]}",
            )
            if st.button("Go to selected result"):
                st.session_state["page_number"] = selected_page
                st.rerun()
        else:
            st.text("No matching pages.")

    page_number = int(st.session_state["page_number"])
    previous, position, following = st.columns([1, 3, 1])
    with previous:
        if st.button("Previous page", disabled=page_number <= 1):
            st.session_state["page_number"] = page_number - 1
            st.rerun()
    with following:
        if st.button("Next page", disabled=page_number >= document.page_count):
            st.session_state["page_number"] = page_number + 1
            st.rerun()
    with position:
        st.number_input(
            "Page number",
            min_value=1,
            max_value=document.page_count,
            step=1,
            key="page_number",
        )

    preview = page_preview(document, int(st.session_state["page_number"]))
    st.text(f"Page {preview.page_number} · {preview.char_count} characters")
    if preview.is_empty:
        st.text("Empty page")
    st.text_area("Page text", value=preview.text, height=360, disabled=True)


def main() -> None:
    st.set_page_config(page_title="LearnBook", layout="wide")
    st.title("LearnBook")
    st.caption(
        "Files are processed in memory on this machine. Nothing is sent "
        "anywhere and nothing is saved."
    )
    _initialize_session_state()
    uploaded_file = st.file_uploader(
        "Upload a PDF",
        type=["pdf"],
        key="pdf_upload",
        on_change=_record_upload_change,
    )

    event = st.session_state["upload_event"]
    event_changed = event != st.session_state["handled_upload_event"]
    if event_changed:
        st.session_state["handled_upload_event"] = event
        st.session_state["duplicate_upload_hash"] = None
        if uploaded_file is None:
            st.session_state["active_upload_hash"] = None

    if uploaded_file is None:
        st.text("Upload a PDF to begin.")
        return

    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    seen_hashes = st.session_state["seen_upload_hashes"]
    if file_hash in seen_hashes:
        if event_changed:
            st.session_state["duplicate_upload_hash"] = file_hash
    else:
        seen_hashes.add(file_hash)

    if st.session_state["active_upload_hash"] != file_hash:
        st.session_state["active_upload_hash"] = file_hash
        st.session_state["page_number"] = 1

    if st.session_state["duplicate_upload_hash"] == file_hash:
        st.info("This PDF has already been uploaded in this session.")

    documents = st.session_state["extracted_documents"]
    if file_hash not in documents:
        try:
            documents[file_hash] = extract_pdf(file_bytes, Settings())
        except IngestionError as error:
            st.error(error.user_message)
            return

    document = documents[file_hash]
    if document.needs_ocr:
        st.warning(
            "This looks like a scanned PDF. Text extraction is unreliable "
            "until OCR is added."
        )
    for warning in document.warnings:
        st.warning(warning)

    _render_document_summary(document)
    st.subheader("Browse pages")
    _render_page_browser(document, file_hash)
    st.download_button(
        "Download extracted text",
        data=export_text(document),
        file_name="learnbook-extracted.txt",
        mime="text/plain",
    )


main()
