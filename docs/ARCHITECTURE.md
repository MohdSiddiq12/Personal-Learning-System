# Architecture

The intended dependency direction is:

```text
UI -> core -> providers/storage
```

The UI translates user interactions into core operations. Core owns application rules and must not import UI code. Provider and storage implementations sit behind boundaries called by core; this keeps framework and persistence choices replaceable. This milestone creates the package boundaries only and does not implement these layers.