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

STYLE = """<style>
:root {
    --ink: #19312f;
    --muted: #627572;
    --teal: #117c75;
    --teal-soft: #e4f2ef;
    --violet: #7552a3;
    --violet-soft: #f0eafa;
    --coral: #bb5e48;
    --line: #dce6e2;
    --paper: #ffffff;
}
[data-testid="stAppViewContainer"] {
    background-color: #f4f7f5;
    background-image: linear-gradient(#eaf0ed 1px, transparent 1px),
        linear-gradient(90deg, #eaf0ed 1px, transparent 1px);
    background-size: 28px 28px;
}
[data-testid="stHeader"] { background: transparent; }
.main .block-container { max-width: 1240px; padding-top: 2.25rem; }
.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label {
    color: var(--ink);
}
.stApp h1 {
    font-family: "Aptos Display", "Trebuchet MS", sans-serif;
    font-size: 2.35rem;
    font-weight: 700;
    line-height: 1.08;
}
.stApp h2, .stApp h3 { font-family: "Aptos Display", "Trebuchet MS", sans-serif; }
.stApp [data-testid="stCaptionContainer"] p { color: var(--muted); }
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--paper);
    border-color: var(--line);
    border-radius: 8px;
}
[data-testid="stFileUploader"] section {
    background: #f8fbf9;
    border: 1px dashed #80aaa4;
    border-radius: 6px;
}
[data-testid="stMetric"] {
    background: #f3f8f6;
    border-left: 3px solid var(--teal);
    border-radius: 5px;
    padding: 0.6rem 0.75rem;
}
[data-testid="stMetric"] label { color: var(--muted); }
.stButton > button, .stDownloadButton > button {
    border-radius: 5px;
    font-weight: 650;
}
.flow-step {
    min-height: 96px;
    border-top: 3px solid var(--line);
    padding: 0.55rem 0.15rem 0.4rem;
}
.flow-step--you { border-color: var(--teal); }
.flow-step--ai { border-color: var(--violet); }
.flow-step--code { border-color: #aab7b3; }
.flow-step__meta {
    display: block;
    color: var(--muted);
    font: 600 0.68rem/1.4 "Aptos", "Trebuchet MS", sans-serif;
    text-transform: uppercase;
}
.flow-step--you .flow-step__meta { color: var(--teal); }
.flow-step--ai .flow-step__meta { color: var(--violet); }
.flow-step__title {
    display: block;
    margin-top: 0.45rem;
    color: var(--ink);
    font: 700 0.92rem/1.25 "Aptos", "Trebuchet MS", sans-serif;
}
.flow-step__status {
    display: block;
    margin-top: 0.25rem;
    color: var(--muted);
    font: 0.75rem/1.3 "Aptos", "Trebuchet MS", sans-serif;
}
@media (max-width: 700px) {
    .main .block-container { padding: 1.25rem 1rem 2rem; }
    .stApp h1 { font-size: 2rem; }
}
</style>"""

ROADMAP = (
    ("01", "Upload a book", "YOU", "you", "Available"),
    ("02", "Extract pages", "CODE", "code", "Available"),
    ("03", "Map the book", "AI", "ai", "Planned"),
    ("04", "Set preferences", "YOU", "you", "Planned"),
    ("05", "Build a path", "CODE", "code", "Planned"),
    ("06", "Study lessons", "AI", "ai", "Planned"),
    ("07", "Save progress", "CODE", "code", "Planned"),
    ("08", "See what stuck", "CODE", "code", "Planned"),
)


def _record_upload_change() -> None:
    st.session_state["upload_event"] = st.session_state.get("upload_event", 0) + 1


def _jump_to_search_result(search_key: str) -> None:
    st.session_state["page_number"] = st.session_state[search_key]


def _initialize_session_state() -> None:
    st.session_state.setdefault("upload_event", 0)
    st.session_state.setdefault("handled_upload_event", None)
    st.session_state.setdefault("seen_upload_hashes", set())
    st.session_state.setdefault("extracted_documents", {})
    st.session_state.setdefault("active_upload_hash", None)
    st.session_state.setdefault("duplicate_upload_hash", None)
    st.session_state.setdefault("page_number", 1)


def _render_document_summary(document: ExtractedDocument) -> None:
    summary = dict(summary_rows(document))
    with st.container(border=True):
        st.caption("EXTRACTED BOOK")
        st.text(f"Title: {summary['Title']}")
        st.text(f"Author: {summary['Author']}")
        columns = st.columns(4)
        columns[0].metric("Pages", summary["Page count"])
        columns[1].metric("Text pages", summary["Non-empty pages"])
        columns[2].metric("File size", summary["File size"])
        columns[3].metric("Needs OCR", summary["Needs OCR"])
        st.caption(f"SHA-256 · {summary['SHA-256']}")


def _render_roadmap() -> None:
    with st.expander("The learning flow · 8 steps", expanded=False):
        st.caption("Later steps are planned and are not active yet.")
        for start in (0, 4):
            columns = st.columns(4)
            for column, (number, title, owner, owner_class, status) in zip(
                columns, ROADMAP[start : start + 4], strict=True
            ):
                column.html(
                    f'<div class="flow-step flow-step--{owner_class}">'
                    f'<span class="flow-step__meta">{number} · {owner}</span>'
                    f'<span class="flow-step__title">{title}</span>'
                    f'<span class="flow-step__status">{status}</span>'
                    "</div>"
                )


def _render_page_browser(document: ExtractedDocument, file_hash: str) -> None:
    page_column, tools_column = st.columns([1.55, 0.8], gap="large")
    with page_column:
        st.subheader("Read the extracted text")
        page_number = int(st.session_state["page_number"])
        previous, position, following = st.columns([1, 2, 1])
        with previous:
            if st.button("← Previous", disabled=page_number <= 1):
                st.session_state["page_number"] = page_number - 1
                st.rerun()
        with following:
            if st.button("Next →", disabled=page_number >= document.page_count):
                st.session_state["page_number"] = page_number + 1
                st.rerun()
        with position:
            st.number_input(
                "Page",
                min_value=1,
                max_value=document.page_count,
                step=1,
                key="page_number",
                label_visibility="collapsed",
            )

        preview = page_preview(document, int(st.session_state["page_number"]))
        st.progress(
            preview.page_number / document.page_count,
            text=f"Page {preview.page_number} of {document.page_count}",
        )
        st.caption(f"{preview.char_count:,} characters")
        if preview.is_empty:
            st.warning("Empty page")
        st.text_area("Page text", value=preview.text, height=420, disabled=True)

    with tools_column:
        st.subheader("Find a passage")
        query = st.text_input("Search this book", key="search_query")
        matching_pages = search_pages(document, query)
        if query:
            if matching_pages:
                search_key = f"search-result-{file_hash[:12]}"
                st.selectbox(
                    "Matching pages",
                    options=matching_pages,
                    format_func=lambda number: f"Page {number}",
                    key=search_key,
                )
                st.button(
                    "Open result",
                    key="open-search-result",
                    on_click=_jump_to_search_result,
                    args=(search_key,),
                )
            else:
                st.caption("No matching pages.")
        st.divider()
        st.subheader("Take it with you")
        st.download_button(
            "Download page-marked text",
            data=export_text(document),
            file_name="learnbook-extracted.txt",
            mime="text/plain",
            use_container_width=True,
        )


def main() -> None:
    st.set_page_config(page_title="LearnBook", layout="wide")
    st.html(STYLE)
    st.caption("LEARNBOOK  /  A PRIVATE READING DESK")
    st.title("LearnBook")
    st.caption(
        "Files are processed in memory on this machine. Nothing is sent "
        "anywhere and nothing is saved."
    )
    _initialize_session_state()
    settings = Settings()
    with st.container(border=True):
        st.caption("START HERE · STEP 01")
        st.subheader("Bring a book to your desk")
        st.text("Choose a PDF to extract its pages. Your file stays on this machine.")
        uploaded_file = st.file_uploader(
            "Upload a PDF",
            type=["pdf"],
            key="pdf_upload",
            on_change=_record_upload_change,
            help=f"PDF only · up to {settings.max_upload_mb} MB",
        )

    event = st.session_state["upload_event"]
    event_changed = event != st.session_state["handled_upload_event"]
    if event_changed:
        st.session_state["handled_upload_event"] = event
        st.session_state["duplicate_upload_hash"] = None
        if uploaded_file is None:
            st.session_state["active_upload_hash"] = None

    if uploaded_file is None:
        _render_roadmap()
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
            documents[file_hash] = extract_pdf(file_bytes, settings)
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
    st.subheader("Your book, page by page")
    _render_page_browser(document, file_hash)
    _render_roadmap()


main()
