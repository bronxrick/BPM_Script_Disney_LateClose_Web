import os
import asyncio
from datetime import datetime, timedelta

from playwright.async_api import async_playwright

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


# ---------------- CONFIG ----------------

DISNEY_URL_TEMPLATE = (
    "https://disneyworld.disney.go.com/calendars/five-day/"
    "{start_date}/#/animal-kingdom,hollywood-studios,epcot,magic-kingdom/"
)

TIMEZONE = "America/New_York"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

TRIGGERS = [
    "Special Ticketed Event",
    "Extended Evening Hours",
]

PARK_NAMES = [
    "Magic Kingdom",
    "Epcot",
    "Hollywood Studios",
    "Animal Kingdom",
]

PARK_CALENDAR_MAP = {
    "Magic": "bnh7aisj5egpsf80icbaliupf8@group.calendar.google.com",
    "Epcot": "sjorn67pf45lujp53f2ok7b1e0@group.calendar.google.com",
    "Hollywood": "uvfdae6s9gd7r4nb05a0oqii38@group.calendar.google.com",
    "Animal": "qvdktkbdu72204031ec0e3hmpo@group.calendar.google.com",
}


# ---------------- GOOGLE CALENDAR AUTH ----------------

def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


# ---------------- DATE HELPERS ----------------

def get_monday_for_this_week():
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.date()


def build_disney_url_for_monday(monday_date):
    return DISNEY_URL_TEMPLATE.format(start_date=monday_date.strftime("%Y-%m-%d"))


# ---------------- PLAYWRIGHT SCRAPING ----------------

async def scrape_disney_week(monday_date):
    url = build_disney_url_for_monday(monday_date)
    print(f"[INFO] Loading URL: {url}")

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")

        # Wait for the calendar grid to appear
        await page.wait_for_selector("div.day", timeout=15000)

        # Select all day columns
        day_columns = await page.query_selector_all("div.day")

        for day_index, day_col in enumerate(day_columns):
            date_obj = monday_date + timedelta(days=day_index)

            # Extract text inside this day's column
            day_text = (await day_col.inner_text()).lower()

            for park_full in PARK_NAMES:
                park_short = park_full.split()[0]

                if park_full.lower() not in day_text:
                    continue

                triggers_found = [
                    trig for trig in TRIGGERS if trig.lower() in day_text
                ]

                if triggers_found:
                    results.append(
                        {
                            "date": date_obj,
                            "park_full": park_full,
                            "park_short": park_short,
                            "trigger_texts": triggers_found,
                        }
                    )

        await browser.close()

    return results


# ---------------- EVENT BUILDING ----------------

def build_events_from_scrape(scrape_results):
    events = []

    for item in scrape_results:
        date_obj = item["date"]
        park_short = item["park_short"]

        calendar_id = PARK_CALENDAR_MAP.get(park_short)
        if not calendar_id:
            print(f"[WARN] No calendar mapping for park '{park_short}', skipping.")
            continue

        summary = f"* {park_short} LATE CLOSE *"

        events.append(
            {
                "summary": summary,
                "date": date_obj,
                "calendar_id": calendar_id,
            }
        )

    return events


# ---------------- GOOGLE CALENDAR EVENT CREATION ----------------

def create_all_day_event(service, calendar_id, summary, date_obj):
    event_body = {
        "summary": summary,
        "start": {"date": date_obj.isoformat(), "timeZone": TIMEZONE},
        "end": {"date": (date_obj + timedelta(days=1)).isoformat(), "timeZone": TIMEZONE},
    }

    created = service.events().insert(calendarId=calendar_id, body=event_body).execute()
    print(
        f"[INFO] Created event '{summary}' on {date_obj.isoformat()} "
        f"in calendar {calendar_id} (id={created.get('id')})"
    )


# ---------------- MAIN ----------------

async def async_main():
    print("[INFO] Starting Disney late-close sync...")

    monday = get_monday_for_this_week()
    print(f"[INFO] Using Monday date: {monday.isoformat()}")

    service = get_calendar_service()

    scrape_results = await scrape_disney_week(monday)
    print(f"[INFO] Scrape results count: {len(scrape_results)}")

    events_to_create = build_events_from_scrape(scrape_results)
    print(f"[INFO] Events to create: {len(events_to_create)}")

    for ev in events_to_create:
        create_all_day_event(
            service=service,
            calendar_id=ev["calendar_id"],
            summary=ev["summary"],
            date_obj=ev["date"],
        )

    print("[INFO] Done.")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()