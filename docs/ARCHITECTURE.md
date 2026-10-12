# Architecture

The dependency direction is:

```text
app -> core -> providers/storage
```

The Streamlit app translates user interactions into core operations. App code may import core and configuration, but core must never import the app or Streamlit. Provider and storage implementations sit behind boundaries called by core; this keeps framework and persistence choices replaceable.

PDF ingestion lives in `learnbook.core.ingestion`. Its flow is:

```text
Path or bytes -> size/header checks -> PyMuPDF validation -> ordered page text + metadata/hash
```

The ingestion module is core logic: it has no UI, database, provider, network, OCR, or rendering dependency. Its results keep each page and its 1-based page number separate so later layers can cite source locations.

The local app lives in `learnbook.app`. Pure display transformations live in `view_models.py`; Streamlit is confined to `main.py`. Upload bytes are hashed and extracted in memory, with successful extraction results cached only in the current Streamlit session. No uploaded file is written to disk.