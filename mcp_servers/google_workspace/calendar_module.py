# mcp_servers/google_workspace/calendar_module.py
import sys
import os
import datetime
from googleapiclient.discovery import build

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from core.authentication import GoogleAuth

class CalendarManager:
    def __init__(self):
        self.creds = GoogleAuth.get_creds()
        self.service = build('calendar', 'v3', credentials=self.creds)

    def _format_iso_time(self, iso_string):
        try:
            if 'T' not in iso_string: return iso_string
            date_part, time_zone_part = iso_string.split('T')
            return f"{date_part} {time_zone_part[:5]}"
        except:
            return iso_string

    def is_time_free(self, start_time: str, end_time: str):
        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            if events:
                conflict = events[0]
                summary = conflict.get('summary', '(Bez názvu)')
                c_start = conflict['start'].get('dateTime', conflict['start'].get('date'))
                c_end = conflict['end'].get('dateTime', conflict['end'].get('date'))
                return False, f"Kolize: V čase {self._format_iso_time(c_start)} - {self._format_iso_time(c_end)} už máš naplánováno: '{summary}'."

            return True, "Volno."
        except Exception as e:
            return False, f"Chyba při kontrole kalendáře: {str(e)}"

    def add_event(self, summary: str, start_time: str, end_time: str, description: str = ""):
        is_free, msg = self.is_time_free(start_time, end_time)
        if not is_free:
            return {"status": "error", "message": f"Nelze vytvořit událost. {msg}"}

        try:
            event = {
                'summary': summary, 'description': description,
                'start': {'dateTime': start_time, 'timeZone': 'Europe/Prague'},
                'end': {'dateTime': end_time, 'timeZone': 'Europe/Prague'},
            }
            self.service.events().insert(calendarId='primary', body=event).execute()
            return {"status": "success", "message": f"Událost '{summary}' úspěšně vytvořena."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_events_in_range(self, start_time: str, end_time: str):
        try:
            events_result = self.service.events().list(
                calendarId='primary', timeMin=start_time, timeMax=end_time,
                singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            if not events:
                return {"status": "success", "message": f"V tomto období nemáš žádné události."}

            output = [f"[{self._format_iso_time(e['start'].get('dateTime', e['start'].get('date')))}] {e['summary']}" for e in events]
            return {"status": "success", "events": output}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_event(self, event_name: str):
        try:
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(calendarId='primary', timeMin=now, q=event_name, singleEvents=True).execute()
            events = events_result.get('items', [])

            if not events: return {"status": "error", "message": f"Událost '{event_name}' nenalezena."}

            self.service.events().delete(calendarId='primary', eventId=events[0]['id']).execute()
            return {"status": "success", "message": f"Událost '{events[0]['summary']}' smazána."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_upcoming_events(self, max_results: int = 5):
        try:
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(calendarId='primary', timeMin=now, maxResults=max_results, singleEvents=True, orderBy='startTime').execute()
            events = events_result.get('items', [])

            if not events: return {"status": "success", "message": "Žádné nadcházející události."}

            output = [f"[{self._format_iso_time(e['start'].get('dateTime', e['start'].get('date')))}] {e['summary']}" for e in events]
            return {"status": "success", "events": output}
        except Exception as e:
            return {"status": "error", "message": str(e)}




cal_mgr = CalendarManager()

def register_calendar(mcp):
    """Tato funkce naučí hlavní MCP server pracovat s kalendářem."""

    @mcp.tool()
    def kalendar_vypis_udalosti(max_results: int = 5) -> str:
        """Vypíše uživateli nadcházející události v kalendáři."""
        res = cal_mgr.list_upcoming_events(max_results)
        if res["status"] == "success" and "events" in res:
            return "Nadcházející události:\n" + "\n".join(res["events"])
        return res.get("message", "Chyba.")

    @mcp.tool()
    def kalendar_pridej_udalost(summary: str, start_time: str, end_time: str, description: str = "") -> str:
        """
        Vytvoří novou událost v kalendáři.
        Časy MUSÍ být ve formátu ISO 8601 (např. 2026-04-03T15:00:00Z).
        """
        return cal_mgr.add_event(summary, start_time, end_time, description).get("message", "Chyba při vytváření.")

    @mcp.tool()
    def kalendar_smaz_udalost(event_name: str) -> str:
        """Smaže nadcházející událost z kalendáře podle jejího názvu."""
        return cal_mgr.delete_event(event_name).get("message", "Chyba při mazání.")

    @mcp.tool()
    def kalendar_vypis_obdobi(start_time: str, end_time: str) -> str:
        """
        Vypíše události v kalendáři pro konkrétní časové rozmezí.
        Použij pro dotazy jako 'Co dělám 22. dubna?' nebo 'Mám dneska volno?'.
        Časy MUSÍ být ve formátu ISO 8601.
        """
        res = cal_mgr.get_events_in_range(start_time, end_time)
        if res["status"] == "success" and "events" in res:
            return f"Události v období:\n" + "\n".join(res["events"])
        return res.get("message", "Žádné události.")