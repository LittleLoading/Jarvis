# interfaces/web/app.py
import time
import os
import sys
import asyncio
from flask import Flask, render_template, request, jsonify

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT_DIR not in sys.path: sys.path.append(ROOT_DIR)

from jarvis_hosts.core_client import JarvisAgent
import jarvis_hosts.memory as chat_manager
import widget_service as widgets

app = Flask(__name__)
jarvis_bot = JarvisAgent()


@app.route('/')
def home():
    return render_template('index.html')


# --- TVÉ ENDPOINTY PRO CHATY (Beze změny) ---
@app.route('/api/chats', methods=['GET'])
def get_chat_list(): return jsonify(chat_manager.get_all_chats())


@app.route('/api/chats', methods=['POST'])
def create_new_chat(): return jsonify(chat_manager.create_chat())


@app.route('/api/chats/<chat_id>', methods=['GET'])
def get_chat_history(chat_id):
    chat = chat_manager.get_chat(chat_id)
    return jsonify(chat) if chat else (jsonify({"error": "Chat not found"}), 404)


@app.route('/api/chats/<chat_id>', methods=['DELETE'])
def delete_chat_route(chat_id):
    return jsonify({"status": "deleted"}) if chat_manager.delete_chat(chat_id) else (jsonify({"error": "Not found"}),
                                                                                     404)


@app.route('/api/chats/<chat_id>', methods=['PUT'])
def rename_chat_route(chat_id):
    title = request.json.get("title")
    if title:
        chat_manager.update_title(chat_id, title)
        return jsonify({"status": "renamed", "new_title": title})
    return jsonify({"error": "No title"}), 400


# --- TVŮJ HLAVNÍ CHAT ENDPOINT ---
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    chat_id = data.get('chat_id')

    if not user_message or not chat_id:
        return jsonify({'error': 'Prázdná zpráva.'}), 400

    start_time = time.time()
    try:
        # Voláme nového Jarvisa, vrací dict s 'reply' a 'new_title'
        response_data = asyncio.run(jarvis_bot.process_message(user_message, chat_id))

        return jsonify({
            'reply': response_data['reply'],
            'tokens': 0,
            'latency': round((time.time() - start_time) * 1000),
            'new_title': response_data.get('new_title')
        })
    except Exception as e:
        print(f"Chyba: {e}")
        return jsonify({'error': str(e)}), 500


# --- TVŮJ DASHBOARD ENDPOINT ---
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    return jsonify({
        'weather': widgets.get_real_weather(),
        'schedule': widgets.get_user_schedule()
    })


if __name__ == '__main__':
    app.run(debug=True)