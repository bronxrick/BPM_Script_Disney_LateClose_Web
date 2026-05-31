# disney_scraper.py

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

TRIGGERS = [
    "Special Ticketed Event",
    "Extended Evening Hours",
]

BASE_URL = (
    "https://disneyworld.disney.go.com/calendars/five-day/{}/"
    "#/animal-kingdom,hollywood-studios,epcot,magic-kingdom/"
)

# ----
# Date helper
# ----
def get_start_date():
    return datetime.now().date()

# ----
# Park name mapping
# ----
def park_from_content_id(content_id):
    cid = content_id.lower()

    if "animal-kingdom" in cid:
        return "Disney's Animal Kingdom", "Animal Kingdom"
    if "hollywood-studios" in cid:
        return "Disney's Hollywood Studios", "Hollywood Studios"
    if "epcot" in cid:
        return "EPCOT", "Epcot"
    if "magic-kingdom" in cid:
        return "Magic Kingdom Park", "Magic Kingdom"

    return content_id, content_id.title()

# ----
# Normalize AM/PM to lowercase
# ----
def normalize_ampm(text):
    return (
        text.replace("AM", "am")
            .replace("PM", "pm")
            .replace("Am", "am")
            .replace("Pm", "pm")
    )

# ----
# Convert "9:00 AM to 11:00 PM" -> {"open": "9:00 pm", "close": "11:00pm"}
# Close time removes the space before am/pm
# ----
def parse_hours_to_dict(hours_str):
    if not hours_str or "to" not in hours_str.lower():
        return None

    parts = hours_str.split("to")
    if len(parts) != 2:
        return None

    open_raw = parts[0].strip()
    close_raw = parts[1].strip()

    open_norm = normalize_ampm(open_raw)
    close_norm = normalize_ampm(close_raw).replace(" ", "")

    return {"open": open_norm, "close": close_norm}

# ----
# Extract visible hours block
# ----
async def extract_visible_hours(block):
    sched_el = await block.query_selector("span.schedules")
    if not sched_el:
        return None

    hours = (await sched_el.inner_text()).strip()
    if not hours:
        return None

    if hours == "-":
        return None

    if "to" not in hours.lower():
        return None

    return parse_hours_to_dict(hours)

async def extract_hours_pattern_b(block):
    return await extract_visible_hours(block)

async def extract_hours_pattern_a(block):
    return await extract_visible_hours(block)

# ----
# Normalize trigger text
# ----
def normalize_trigger_label(text):
    if "Special Ticketed Event" in text:
        return "Special Ticketed Event"
    if "Extended Evening Hours" in text:
        return "Extended Evening Hours"
    return text

# ----
# Main scraper
# ----
async def scrape_disney_week(start_date):
    url = BASE_URL.format(start_date.strftime("%Y-%m-%d"))
    print("[INFO] Loading URL: {}".format(url))

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)

        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
                "Gecko/20100101 Firefox/122.0"
            )
        )

        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(1500)

        await page.wait_for_selector("div.date-range", timeout=60000)
        date_range_el = await page.query_selector("div.date-range")
        date_spans = await date_range_el.query_selector_all("span.date")

        date_list = []
        for span in date_spans:
            txt = (await span.inner_text()).strip()
            parts = txt.split(",")
            if len(parts) == 2:
                try:
                    day_int = int(parts[1].strip())
                    date_obj = start_date.replace(day=day_int)
                    date_list.append(date_obj)
                except Exception:
                    date_list.append(None)
            else:
                date_list.append(None)

        content_regions = await page.query_selector_all(
            "div.content[id$='-park-hours-content']"
        )

        results = []

        for content_el in content_regions:
            content_id = await content_el.get_attribute("id")
            if not content_id:
                continue

            park_full, park_short = park_from_content_id(content_id)

            row_el = await content_el.query_selector("div.row")
            if not row_el:
                continue

            day_columns = await row_el.query_selector_all("div.day")

            for idx, day_col in enumerate(day_columns):
                if idx >= len(date_list):
                    continue

                date_obj = date_list[idx]
                if not date_obj:
                    continue

                hours_blocks = await day_col.query_selector_all("div.hours")

                for block in hours_blocks:

                    # ----
                    # PATTERN A (anchor-based)
                    # ----
                    anchor_el = await block.query_selector("a[aria-label], finder-anchor[aria-label]")
                    if anchor_el:
                        aria = (await anchor_el.get_attribute("aria-label")) or ""
                        for trig in TRIGGERS:
                            if trig in aria:
                                hours = await extract_hours_pattern_a(block)
                                if hours:
                                    results.append(
                                        {
                                            "date": date_obj,
                                            "park_full": park_full,
                                            "park_short": park_short,
                                            "trigger_texts": [trig],
                                            "hours": hours,
                                        }
                                    )
                                break

                    # ----
                    # PATTERN B (name-based)
                    # ----
                    name_el = await block.query_selector("span.name")
                    if not name_el:
                        continue

                    name_text = (await name_el.inner_text()).strip()

                    if name_text not in TRIGGERS:
                        continue

                    hours = await extract_hours_pattern_b(block)
                    if not hours:
                        continue

                    results.append(
                        {
                            "date": date_obj,
                            "park_full": park_full,
                            "park_short": park_short,
                            "trigger_texts": [normalize_trigger_label(name_text)],
                            "hours": hours,
                        }
                    )

        await browser.close()
        return results

# ----
# Preview results
# ----
def preview_results(results):
    print("\n===== NEXT 5 DAYS PREVIEW =====")
    if not results:
        print("No late-close events found.")
        print("================================")
        return

    for r in results:
        print(
            "{} | {} | {} | open={} close={}".format(
                r["date"],
                r["park_short"],
                ", ".join(r["trigger_texts"]),
                r["hours"]["open"],
                r["hours"]["close"],
            )
        )

    print("================================")