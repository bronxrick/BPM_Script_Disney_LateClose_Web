# config.py

TIMEZONE = "America/New_York"

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
    "Magic Kingdom": "bnh7aisj5egpsf80icbaliupf8@group.calendar.google.com",
    "Epcot": "sjorn67pf45lujp53f2ok7b1e0@group.calendar.google.com",
    "Hollywood Studios": "uvfdae6s9gd7r4nb05a0oqii38@group.calendar.google.com",
    "Animal Kingdom": "qvdktkbdu72204031ec0e3hmpo@group.calendar.google.com",
}
DISNEY_URL_TEMPLATE = (
    "https://disneyworld.disney.go.com/calendars/five-day/"
    "{start_date}/#/animal-kingdom,hollywood-studios,epcot,magic-kingdom/"
)