# google_calendar.py

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError

# ----
# Google Calendar API scopes
# ----
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ----
# Load or refresh credentials, auto-recover if token is invalid
# ----
def get_calendar_service():
    creds = None

    # Load existing token if present
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception:
            # Corrupted token file
            os.remove("token.json")
            creds = None

    # Attempt refresh if token exists
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            # Token expired or revoked
            print("[WARN] Google token expired or revoked. Re-authentication required.")
            try:
                os.remove("token.json")
            except Exception:
                pass
            creds = None

    # If no valid credentials, run OAuth flow
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

# ----
# Check if an event already exists on a given date
# ----
def event_exists(service, calendar_id, summary, date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")

    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=date_str + "T00:00:00Z",
        timeMax=date_str + "T23:59:59Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])

    for ev in events:
        if ev.get("summary", "") == summary:
            return True

    return False

# ----
# Create an all-day event
# ----
def create_all_day_event(service, calendar_id, summary, date_obj):
    date_str = date_obj.strftime("%Y-%m-%d")

    event_body = {
        "summary": summary,
        "start": {"date": date_str},
        "end": {"date": date_str},
    }

    service.events().insert(
        calendarId=calendar_id,
        body=event_body
    ).execute()