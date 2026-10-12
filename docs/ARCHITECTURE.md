# Architecture

The intended dependency direction is:

```text
UI -> core -> providers/storage
```

The UI translates user interactions into core operations. Core owns application rules and must not import UI code. Provider and storage implementations sit behind boundaries called by core; this keeps framework and persistence choices replaceable.

PDF ingestion lives in `learnbook.core.ingestion`. Its flow is:

```text
Path or bytes -> size/header checks -> PyMuPDF validation -> ordered page text + metadata/hash
```

The ingestion module is core logic: it has no UI, database, provider, network, OCR, or rendering dependency. Its results keep each page and its 1-based page number separate so later layers can cite source locations.