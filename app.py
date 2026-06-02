# app.py — Flask web interface for Disney Late Close Calendar Extractor

import asyncio
import concurrent.futures
import json
import os
from datetime import date

from flask import Flask, render_template, jsonify, request, redirect, session, url_for

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build

from disney_scraper import get_start_date, scrape_disney_week
from config import PARK_CALENDAR_MAP

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'disney-lc-web-secret-2024')

SCOPES = ['https://www.googleapis.com/auth/calendar']

PARK_TITLE_MAP = {
    "Hollywood Studios": "HOLLYWOOD",
    "Epcot": "EPCOT",
    "Magic Kingdom": "MAGIC",
    "Animal Kingdom": "ANIMAL",
}

# DATA_DIR: where token.json and credentials.json live.
# Locally: current directory. On Railway: mount a volume at /data and set DATA_DIR=/data
DATA_DIR = os.environ.get('DATA_DIR', '.')
TOKEN_PATH = os.path.join(DATA_DIR, 'token.json')
CREDENTIALS_PATH = os.path.join(DATA_DIR, 'credentials.json')

# Seed credentials.json from env var on first deploy (Railway secret → file)
_creds_env = os.environ.get('GOOGLE_CREDENTIALS_JSON')
if _creds_env:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CREDENTIALS_PATH, 'w') as _f:
            _f.write(_creds_env)
        print('[STARTUP] credentials.json written to', CREDENTIALS_PATH)
    except Exception as _e:
        print('[STARTUP] ERROR writing credentials.json:', _e)
else:
    print('[STARTUP] GOOGLE_CREDENTIALS_JSON env var not set')

# Seed token.json from env var on every startup (always overwrite so updates take effect)
_token_env = os.environ.get('GOOGLE_TOKEN_JSON')
if _token_env:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(TOKEN_PATH, 'w') as _f:
            _f.write(_token_env)
        print('[STARTUP] token.json written to', TOKEN_PATH)
    except Exception as _e:
        print('[STARTUP] ERROR writing token.json:', _e)
else:
    print('[STARTUP] GOOGLE_TOKEN_JSON env var not set')

# Only allow HTTP OAuth in local/dev mode. Railway serves HTTPS so this stays off.
if not os.environ.get('PRODUCTION'):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


# ---- Google Calendar helpers ----

def load_credentials():
    if not os.path.exists(TOKEN_PATH):
        return None
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    except Exception:
        return None

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
        except RefreshError:
            os.remove(TOKEN_PATH)
            return None

    return creds if creds.valid else None


def get_calendar_service():
    creds = load_credentials()
    if not creds:
        return None
    return build('calendar', 'v3', credentials=creds)


def event_exists(service, calendar_id, summary, date_obj):
    date_str = date_obj.strftime('%Y-%m-%d')
    result = service.events().list(
        calendarId=calendar_id,
        timeMin=date_str + 'T00:00:00Z',
        timeMax=date_str + 'T23:59:59Z',
        singleEvents=True,
        orderBy='startTime',
    ).execute()
    return any(ev.get('summary') == summary for ev in result.get('items', []))


def create_all_day_event(service, calendar_id, summary, date_obj):
    date_str = date_obj.strftime('%Y-%m-%d')
    event_body = {
        'summary': summary,
        'start': {'date': date_str},
        'end': {'date': date_str},
    }
    service.events().insert(calendarId=calendar_id, body=event_body).execute()


# ---- Routes ----

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/auth/google')
def auth_google():
    if not os.path.exists(CREDENTIALS_PATH):
        return 'credentials.json not found on server. Set GOOGLE_CREDENTIALS_JSON env var.', 500

    flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=SCOPES,
        redirect_uri=url_for('auth_callback', _external=True),
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true',
    )
    session['oauth_state'] = state
    return redirect(auth_url)


@app.route('/auth/callback')
def auth_callback():
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=SCOPES,
        state=session.get('oauth_state'),
        redirect_uri=url_for('auth_callback', _external=True),
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TOKEN_PATH, 'w') as f:
        f.write(creds.to_json())
    return redirect('/')


@app.route('/api/auth-status')
def auth_status():
    service = get_calendar_service()
    return jsonify({'authenticated': service is not None})


@app.route('/api/debug')
def debug():
    token_exists = os.path.exists(TOKEN_PATH)
    creds_exists = os.path.exists(CREDENTIALS_PATH)
    token_env_set = bool(os.environ.get('GOOGLE_TOKEN_JSON'))
    creds_env_set = bool(os.environ.get('GOOGLE_CREDENTIALS_JSON'))

    creds_error = None
    creds_expired = None
    creds_valid = None
    if token_exists:
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            creds_expired = creds.expired
            creds_valid = creds.valid
        except Exception as e:
            creds_error = str(e)

    # Show all env var KEYS (not values) so we can see what Railway is injecting
    env_keys = sorted(os.environ.keys())

    return jsonify({
        'data_dir': DATA_DIR,
        'token_path': TOKEN_PATH,
        'token_file_exists': token_exists,
        'token_env_set': token_env_set,
        'credentials_file_exists': creds_exists,
        'credentials_env_set': creds_env_set,
        'creds_expired': creds_expired,
        'creds_valid': creds_valid,
        'creds_error': creds_error,
        'all_env_keys': env_keys,
    })


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    service = get_calendar_service()
    if not service:
        return jsonify({'error': 'Not authenticated with Google Calendar'}), 401

    logs = ['[INFO] Starting Disney Late-Close scan...']
    start_date = get_start_date()
    logs.append('[INFO] Using start date: {}'.format(start_date))

    try:
        # Run Playwright in a thread so asyncio.run() gets a clean event loop
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, scrape_disney_week(start_date))
            scrape_results = future.result(timeout=120)
    except concurrent.futures.TimeoutError:
        return jsonify({'error': 'Scrape timed out after 120s', 'logs': logs}), 504
    except Exception as e:
        logs.append('[ERROR] Scrape failed: {}'.format(str(e)))
        return jsonify({'error': str(e), 'logs': logs}), 500

    logs.append('[INFO] Found {} park entries from scrape'.format(len(scrape_results)))
    logs.append('')
    logs.append('===== EVENT ACTION PREVIEW =====')

    events = []
    for item in scrape_results:
        date_obj = item['date']
        park_short = item['park_short']
        calendar_id = PARK_CALENDAR_MAP.get(park_short)

        if not calendar_id:
            logs.append('[WARN] No calendar mapping for {}'.format(park_short))
            continue

        title_word = PARK_TITLE_MAP.get(park_short, park_short.upper())
        close_time = item['hours']['close']
        summary = '* {} {} CLOSE *'.format(title_word, close_time)

        exists = event_exists(service, calendar_id, summary, date_obj)
        action = 'skip' if exists else 'add'

        if exists:
            logs.append('[SKIP] Duplicate: {} on {}'.format(summary, date_obj))
        else:
            logs.append('[ADD] Will create: {} on {}'.format(summary, date_obj))

        events.append({
            'summary': summary,
            'date': date_obj.isoformat(),
            'calendar_id': calendar_id,
            'action': action,
        })

    logs.append('================================')

    if not events:
        logs.append('[INFO] No late-close events found in the next 5 days.')

    return jsonify({'events': events, 'logs': logs})


@app.route('/api/create-events', methods=['POST'])
def api_create_events():
    service = get_calendar_service()
    if not service:
        return jsonify({'error': 'Not authenticated with Google Calendar'}), 401

    data = request.get_json()
    selected = data.get('events', [])

    logs = ['[INFO] Creating {} selected event(s)...'.format(len(selected))]

    for ev in selected:
        try:
            date_obj = date.fromisoformat(ev['date'])
            create_all_day_event(service, ev['calendar_id'], ev['summary'], date_obj)
            logs.append('[ADD] Created: {} on {}'.format(ev['summary'], ev['date']))
        except Exception as e:
            logs.append('[ERROR] Failed to create {}: {}'.format(ev['summary'], str(e)))

    logs.append('[INFO] Done.')
    return jsonify({'logs': logs})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
