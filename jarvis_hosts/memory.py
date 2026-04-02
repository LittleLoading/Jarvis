# jarvis_hosts/memory.py
import json
import os
import uuid
from datetime import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CHATS_DIR = os.path.join(ROOT_DIR, "data", "chats")
os.makedirs(CHATS_DIR, exist_ok=True)


def create_chat():
    """Vytvoří novou prázdnou konverzaci a vrátí její data."""
    chat_id = str(uuid.uuid4())
    chat_data = {
        "id": chat_id,
        "title": "Nová konverzace...",
        "created_at": datetime.now().isoformat(),
        "messages": []
    }
    _save_chat(chat_id, chat_data)
    return chat_data


def get_all_chats():
    """Vrátí seznam všech chatů pro levý panel."""
    chats = []
    for filename in os.listdir(CHATS_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(CHATS_DIR, filename), "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    chats.append({
                        "id": data["id"],
                        "title": data.get("title", "Neznámý chat"),
                        "created_at": data.get("created_at", "")
                    })
                except Exception:
                    continue
    chats.sort(key=lambda x: x["created_at"], reverse=True)
    return chats


def get_chat(chat_id):
    """Vrátí celou historii konkrétního chatu."""
    path = os.path.join(CHATS_DIR, f"{chat_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_message(chat_id, role, text):
    """Uloží novou zprávu a vrátí aktuální počet zpráv."""
    chat = get_chat(chat_id)
    if chat:
        chat["messages"].append({"role": role, "text": text})
        _save_chat(chat_id, chat)
        return len(chat["messages"])
    return 0


def update_title(chat_id, title):
    """Aktualizuje název chatu."""
    chat = get_chat(chat_id)
    if chat:
        chat["title"] = title
        _save_chat(chat_id, chat)


def _save_chat(chat_id, data):
    """Interní funkce pro zápis do souboru."""
    with open(os.path.join(CHATS_DIR, f"{chat_id}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def delete_chat(chat_id):
    """Smaže historii konverzace."""
    path = os.path.join(CHATS_DIR, f"{chat_id}.json")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False