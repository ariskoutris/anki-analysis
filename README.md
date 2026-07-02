# Anki Learning Dashboard

An interactive Plotly Dash dashboard for analysing your Anki flashcard reviews on FSRS-enabled decks.

![Dashboard screenshot](docs/screenshot.png)

## Setup

```bash
uv run python -m src.app
```

`uv` creates the environment and installs dependencies on first run. Then open <http://127.0.0.1:8050>. Set the `PORT` environment variable to use a different port.

Load your data with the **Sync** button (from a local Anki install) or by uploading an `.apkg` export.
