# interfaces/web/widget_service.py
import os
import sys
import datetime
import requests
from googleapiclient.discovery import build

# --- NAPOJENÍ NA CENTRÁLNÍ OVĚŘOVÁNÍ (Složka core) ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from core.authentication import GoogleAuth


def get_real_weather():
    """Získá aktuální počasí v Praze z Open-Meteo API."""
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=50.08&longitude=14.43&current_weather=true"
        response = requests.get(url)
        data = response.json()

        current = data.get('current_weather', {})
        temp = current.get('temperature')
        code = current.get('weathercode')

        condition, icon = decode_weather_code(code)

        return {
            "temp": f"{temp}°C",
            "location": "Prague, CZ",
            "condition": condition,
            "icon": icon
        }
    except Exception as e:
        print(f"Chyba počasí: {e}")
        return {"temp": "--", "location": "N/A", "condition": "Error", "icon": "alert-circle-outline"}


def decode_weather_code(code):
    if code == 0: return "Clear sky", "sunny-outline"
    if code in [1, 2, 3]: return "Partly cloudy", "partly-sunny-outline"
    if code in [45, 48]: return "Foggy", "cloudy-outline"
    if code in [51, 53, 55, 61, 63, 65]: return "Rain", "rainy-outline"
    if code in [71, 73, 75]: return "Snow", "snow-outline"
    return "Unknown", "cloud-outline"


def get_czech_day_name(date_obj):
    """Vrátí český název dne."""
    days = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"]
    return days[date_obj.weekday()]


def format_friendly_time(start_data):
    """
    Převede Google čas na lidský formát (Dnes, Zítra, Středa...).
    """
    now = datetime.datetime.now()
    today = now.date()
    tomorrow = today + datetime.timedelta(days=1)

    if 'dateTime' in start_data:
        dt_obj = datetime.datetime.fromisoformat(start_data['dateTime'])
        event_date = dt_obj.date()
        time_str = dt_obj.strftime("%H:%M")
        is_all_day = False
    elif 'date' in start_data:
        event_date = datetime.date.fromisoformat(start_data['date'])
        time_str = "Celý den"
        is_all_day = True
    else:
        return "Neznámý čas"

    if event_date == today:
        day_label = "Dnes"
    elif event_date == tomorrow:
        day_label = "Zítra"
    else:
        day_label = get_czech_day_name(event_date)

    days_diff = (event_date - today).days
    if days_diff > 7:
        day_label = event_date.strftime("%d.%m.")

    if is_all_day:
        return day_label
    else:
        return f"{day_label} {time_str}"


def get_user_schedule():
    """Získá události pro Dashboard s využitím centrálního ověřování."""
    # ZDE JE TA HLAVNÍ ZMĚNA: Používáme naši core/authentication.py
    try:
        creds = GoogleAuth.get_creds()
    except Exception as e:
        print(f"Chyba při načítání Google Auth: {e}")
        return [{"time": "Err", "title": "Chyba přihlášení", "color": "red"}]

    if not creds or not creds.valid:
        return [{"time": "Info", "title": "Neplatný token", "color": "orange"}]

    try:
        service = build('calendar', 'v3', credentials=creds)

        now = datetime.datetime.utcnow()
        one_week_later = (now + datetime.timedelta(days=7)).isoformat() + 'Z'
        now_iso = now.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now_iso,
            timeMax=one_week_later,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return [{"time": "", "title": "Žádné plány na týden", "color": "gray"}]

        formatted_events = []
        colors = ["var(--accent-cyan)", "var(--accent-purple)", "var(--accent-green)", "#f43f5e", "#f59e0b"]

        for i, event in enumerate(events):
            friendly_time = format_friendly_time(event['start'])

            formatted_events.append({
                "time": friendly_time,
                "title": event.get('summary', 'Bez názvu'),
                "color": colors[i % len(colors)],
                "link": event.get('htmlLink', '#')
            })

        return formatted_events

    except Exception as e:
        print(f"Chyba Google Calendar (Dashboard): {e}")
        return [{"time": "Err", "title": "Chyba API", "color": "red"}]