# main.py

import asyncio
import threading
import customtkinter as ctk

from disney_scraper import (
    get_start_date,
    scrape_disney_week,
    preview_results,
)

from google_calendar import (
    get_calendar_service,
    create_all_day_event,
    event_exists,
)

from config import PARK_CALENDAR_MAP
from delorean_console import DeLoreanConsole

# ----
# Map park short names to title words
# ----
PARK_TITLE_MAP = {
    "Hollywood Studios": "HOLLYWOOD",
    "Epcot": "EPCOT",
    "Magic Kingdom": "MAGIC",
    "Animal Kingdom": "ANIMAL",
}

# ----
# Build event objects with new title format:
# * EPCOT 11:00 pm CLOSE *
# ----
def build_events(scrape_results, log):
    events = []

    for item in scrape_results:
        date_obj = item["date"]
        park_short = item["park_short"]
        calendar_id = PARK_CALENDAR_MAP.get(park_short)

        if not calendar_id:
            log.write("[WARN] No calendar mapping for {}".format(park_short))
            continue

        title_word = PARK_TITLE_MAP.get(park_short, park_short.upper())

        close_time = item["hours"]["close"]
        summary = "* {} {} CLOSE *".format(title_word, close_time)

        events.append(
            {
                "summary": summary,
                "date": date_obj,
                "calendar_id": calendar_id,
            }
        )

    return events

# ----
# Main async workflow
# ----
async def async_main(log: DeLoreanConsole):
    log.write("[INFO] Starting Disney Late-Close Automation")

    start_date = get_start_date()
    log.write("[INFO] Using start date: {}".format(start_date))

    scrape_results = await scrape_disney_week(start_date)
    preview_results(scrape_results)

    events = build_events(scrape_results, log)

    service = get_calendar_service()

    log.write("")
    log.write("===== EVENT ACTION PREVIEW =====")

    actions = []

    for ev in events:
        exists = event_exists(
            service,
            ev["calendar_id"],
            ev["summary"],
            ev["date"]
        )

        if exists:
            log.write("[SKIP] Duplicate: {} on {}".format(
                ev["summary"], ev["date"]
            ))
            actions.append(("skip", ev))
        else:
            log.write("[ADD] Will create: {} on {}".format(
                ev["summary"], ev["date"]
            ))
            actions.append(("add", ev))

    log.write("================================")
    log.write("")

    selected_events = log.show_confirmation_panel(actions)

    if selected_events is None:
        log.write("[INFO] User cancelled. No events created.")
        return

    log.write("[INFO] Creating selected events...")

    for ev in selected_events:
        create_all_day_event(
            service,
            ev["calendar_id"],
            ev["summary"],
            ev["date"],
        )
        log.write("[ADD] Created: {} on {}".format(ev["summary"], ev["date"]))

    log.write("[INFO] Done.")

# ----
# Thread wrapper
# ----
def run_async_in_thread(log: DeLoreanConsole):
    asyncio.run(async_main(log))

# ----
# Entry point
# ----
def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    console = DeLoreanConsole()

    worker = threading.Thread(target=run_async_in_thread, args=(console,), daemon=True)
    worker.start()

    console.mainloop()

if __name__ == "__main__":
    main()