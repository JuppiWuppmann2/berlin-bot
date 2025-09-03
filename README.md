# Berlin VIZ Bluesky Bot

## 🔧 Funktionen
- Scraper (GitHub Actions) holt Baustellen/Sperrungen von viz.berlin.de.
- Speichert Stand in `state.json`.
- Bot (Render) prüft Unterschiede und postet automatisch:
  - 🆕 Neue Meldungen
  - ✅ Behoben-Meldungen
- Postet auf **Bluesky**.

## 🚀 Setup
1. Repo forken oder clonen.
2. GitHub Secrets (für Actions): keine nötig.
3. Render-Dienst erstellen:
   - `BSKY_HANDLE` (dein Bluesky-Handle, z. B. `name.bsky.social`)
   - `BSKY_PASSWORD` (App-Passwort von Bluesky)
4. Deploy starten → Bot läuft 24/7.

