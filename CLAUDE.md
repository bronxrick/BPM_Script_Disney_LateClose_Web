# script_Disney_LateClose

Original Python script (CLI/desktop) that scrapes Disney World late-close hours and pushes events to Google Calendar. The web app version lives in `../App_Disney_LateClose/`.

## Files

| File | Description |
|---|---|
| `main.py` | Entry point |
| `disney_scraper.py` | Fetches events from ThemeParks.wiki JSON API |
| `google_calendar.py` | Google Calendar push/update |
| `disney_late_close_to_calendar.py` | Core sync logic |
| `delorean_console.py` | Time/date utility |
| `confirmation_modal.py` | UI confirmation dialog |
| `config.py` | Park names, calendar IDs, trigger keywords |

## Stack
- Python, Google Calendar API
- No browser scraping — uses ThemeParks.wiki JSON API

## Running
```powershell
python main.py
```

## Sensitive files — never commit
- `credentials.json` — Google OAuth client credentials
- `token.json` — OAuth refresh token
