# mcp_servers/google_workspace/drive_module.py
import sys
import os
from googleapiclient.discovery import build


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from core.authentication import GoogleAuth


class DriveManager:
    def __init__(self):
        self.creds = GoogleAuth.get_creds()
        self.service = build('drive', 'v3', credentials=self.creds)

    def list_files(self, page_size: int = 10):
        """Vrátí seznam nejnovějších souborů."""
        try:
            results = self.service.files().list(
                pageSize=page_size,
                fields="nextPageToken, files(id, name, mimeType)",
                q="trashed = false",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            return {"status": "success", "files": results.get('files', [])}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_file_id(self, filename: str, mime_type: str = None):
        """Najde ID souboru podle přesného jména."""
        try:
            safe_filename = filename.replace("'", "\\'")
            query = f"name = '{safe_filename}' and trashed = false"
            if mime_type:
                query += f" and mimeType = '{mime_type}'"

            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()

            files = results.get('files', [])
            return files[0]['id'] if files else None
        except Exception:
            return None

    def find_file_details(self, filename: str):
        """Najde soubory obsahující řetězec a vrátí detaily."""
        try:
            safe_filename = filename.replace("'", "\\'")
            query = f"name contains '{safe_filename}' and trashed = false"

            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, webViewLink)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageSize=5
            ).execute()

            files = results.get('files', [])
            if not files:
                return {"status": "error", "message": f"Soubor '{filename}' nebyl nalezen."}

            found_list = [f"Nalezeno: {f['name']} (Odkaz: {f['webViewLink']})" for f in files]
            return {"status": "success", "message": "\n".join(found_list)}
        except Exception as e:
            return {"status": "error", "message": str(e)}


drive_mgr = DriveManager()

def register_drive(mcp):
    """Zaregistruje nástroje pro práci s Diskem do MCP serveru."""

    @mcp.tool()
    def disk_vypis_soubory(page_size: int = 10) -> str:
        """Vypíše seznam nejnovějších souborů na Google Disku."""
        res = drive_mgr.list_files(page_size)
        if res["status"] == "success":
            if not res["files"]: return "Disk je prázdný."
            return "Soubory na disku:\n" + "\n".join([f"- {f['name']} ({f['mimeType']})" for f in res["files"]])
        return res.get("message", "Chyba při čtení disku.")

    @mcp.tool()
    def disk_najdi_soubor(filename: str) -> str:
        """
        Vyhledá soubor na Google Disku podle názvu.
        Vrátí název nalezeného souboru a přímý odkaz (link) na něj.
        """
        res = drive_mgr.find_file_details(filename)
        return res.get("message", "Chyba při hledání.")