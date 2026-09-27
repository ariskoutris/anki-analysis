# Anki Learning Dashboard

An interactive Plotly Dash dashboard for analysing your Anki flashcard reviews on FSRS-enabled decks.

![Dashboard screenshot](docs/screenshot.png)

## Setup

```bash
uv run python -m src.app
```

`uv` creates the environment and installs dependencies on first run. Then open <http://127.0.0.1:8050>.

Load your data with the **Sync** button, which downloads your collection from AnkiWeb, or by uploading an `.apkg` export. The first Sync asks for your AnkiWeb email and password. Only the sync key AnkiWeb returns is kept (in `data/ankiweb.json`), never the password. Delete that file to log out. Syncing only downloads; nothing is sent back to AnkiWeb.

## Desktop app (macOS)

To launch the dashboard like a normal app, in its own window with no terminal or browser needed:

```bash
./scripts/install-launcher.sh
```

This installs **Anki Dashboard** into `~/Applications`, where Spotlight, Launchpad and the Dock can find it. Opening it syncs from AnkiWeb and shows the dashboard. Closing the window shuts the server down.

- The app runs this checkout of the repo, so code changes apply on the next launch. Re-run the script if you move the repo folder.
- On first launch, macOS may ask for permission to access the folder that holds the repo (e.g. Documents). Allow it.
- Logs: `~/Library/Logs/anki-dashboard.log`. Without the launcher, the same window opens with `uv run python -m src.desktop`.
