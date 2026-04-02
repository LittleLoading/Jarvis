# mcp_servers/google_workspace/gmail_module.py
import sys
import os
import base64
from email.message import EmailMessage
from googleapiclient.discovery import build


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from core.authentication import GoogleAuth


class GmailManager:
    def __init__(self):
        self.creds = GoogleAuth.get_creds()
        self.service = build('gmail', 'v1', credentials=self.creds)

    def send_email(self, to, subject, body):
        try:
            message = EmailMessage()
            message.set_content(body)
            message['To'] = to
            message['Subject'] = subject
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {'raw': encoded_message}
            sent = self.service.users().messages().send(userId="me", body=create_message).execute()
            return {"status": "success", "message": f"Email úspěšně odeslán. (ID: {sent['id']})"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def reply_to_email(self, thread_id, body):
        """Odešle odpověď do existujícího vlákna."""
        try:
            message = EmailMessage()
            message.set_content(body)
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {
                'raw': encoded_message,
                'threadId': thread_id
            }
            sent = self.service.users().messages().send(userId="me", body=create_message).execute()
            return {"status": "success", "message": f"Odpověď odeslána. (ID: {sent['id']})"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def trash_email(self, message_id):
        """Přesune zprávu do koše."""
        try:
            self.service.users().messages().trash(userId="me", id=message_id).execute()
            return {"status": "success", "message": "Zpráva byla přesunuta do koše."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def read_emails(self, query='is:unread', max_results=5):
        """Vrací maily včetně ID a Thread ID."""
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            output = []

            if not messages:
                return {"status": "success", "emails": [], "message": "Žádné zprávy."}

            for msg in messages:
                txt = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                payload = txt['payload']
                headers = payload.get('headers', [])

                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Bez předmětu')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Neznámý')

                output.append({
                    "id": msg['id'],
                    "threadId": msg['threadId'],
                    "sender": sender,
                    "subject": subject,
                    "snippet": txt['snippet']
                })

            return {"status": "success", "emails": output}
        except Exception as e:
            return {"status": "error", "message": str(e)}



gmail_mgr = GmailManager()


def register_gmail(mcp):
    """Zaregistruje nástroje pro práci s Gmailem do MCP serveru."""

    @mcp.tool()
    def gmail_precti_neprectene(max_results: int = 5) -> str:
        """Přečte nejnovější nepřečtené emaily (Odesílatel, Předmět a Ukázka textu)."""
        res = gmail_mgr.read_emails(query='is:unread', max_results=max_results)
        if res["status"] == "success":
            if not res["emails"]: return "Nemáš žádné nové nepřečtené zprávy."

            # Naformátování seznamu mailů pro AI
            formatted_emails = []
            for m in res["emails"]:
                formatted_emails.append(
                    f"Od: {m['sender']}\nPředmět: {m['subject']}\nText: {m['snippet']}\n[Thread ID: {m['threadId']}, Msg ID: {m['id']}]")

            return "\n\n---\n\n".join(formatted_emails)

        return res.get("message", "Chyba při čtení emailů.")

    @mcp.tool()
    def gmail_odesli_novy(to: str, subject: str, body: str) -> str:
        """Odešle úplně nový email. 'to' je emailová adresa příjemce."""
        res = gmail_mgr.send_email(to, subject, body)
        return res.get("message", "Chyba při odesílání emailu.")

    @mcp.tool()
    def gmail_odpovez(thread_id: str, body: str) -> str:
        """
        Odpoví na existující emailové vlákno.
        Vyžaduje 'thread_id' získané ze čtení emailů.
        """
        res = gmail_mgr.reply_to_email(thread_id, body)
        return res.get("message", "Chyba při odpovídání na email.")

    @mcp.tool()
    def gmail_smaz_do_kose(message_id: str) -> str:
        """Přesune email do koše na základě jeho 'Msg ID'."""
        res = gmail_mgr.trash_email(message_id)
        return res.get("message", "Chyba při mazání emailu.")