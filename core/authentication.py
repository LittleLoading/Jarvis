# core/authentication.py
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CREDENTIALS_FILE = os.path.join(ROOT_DIR, 'credentials.json')
TOKEN_FILE = os.path.join(ROOT_DIR, 'token.json')

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://mail.google.com/'
]


class GoogleAuth:
    @staticmethod
    def get_creds():
        creds = None

        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except Exception as e:
                print(f"⚠️ Varování: Nelze načíst {TOKEN_FILE} ({e}). Vytvořím nový.")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"⚠️ Varování: Obnova tokenu selhala ({e}). Bude nutné nové přihlášení.")
                    creds = None

            if not creds:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Kritická chyba: Chybí soubor {CREDENTIALS_FILE}! "
                        "Stáhni ho znovu z Google Cloud Console a vlož do hlavní složky."
                    )

                print("🔒 Spouštím Google Ověření - podívej se do prohlížeče...")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
                token.write(creds.to_json())

        return creds