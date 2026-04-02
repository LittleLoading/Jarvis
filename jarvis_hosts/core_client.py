# jarvis_host/core_client.py
import datetime
import os
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import jarvis_hosts.memory as chat_manager

load_dotenv()


class JarvisAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Chybí GEMINI_API_KEY v .env souboru!")

        self.client = genai.Client(api_key=self.api_key)

       #cesta k mcp serveru
        self.server_script = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'mcp_servers', 'server.py'
        ))

    def _generate_title(self, first_message: str) -> str:
        """Vygeneruje stručný název pro nový chat."""
        try:
            prompt = f"Navrhni velmi stručný název (max 3 slova) pro tuto konverzaci. Neodpovídej na ni. Zpráva: {first_message}"
            response = self.client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return response.text.strip().replace('"', '').replace('*', '')
        except:
            return "Nová konverzace"

    async def process_message(self, user_message: str, chat_id: str = None) -> dict:
        now = datetime.datetime.now()
        current_time_info = now.strftime("%A, %d. %B %Y, %H:%M")


        gemini_history = []
        if chat_id:
            chat_data = chat_manager.get_chat(chat_id)
            if chat_data:
                for msg in chat_data["messages"]:
                    role = "user" if msg["role"] == "user" else "model"
                    gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["text"])]))

        server_params = StdioServerParameters(command="python", args=[self.server_script], env=os.environ.copy())

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                mcp_tools = await session.list_tools()

                gemini_tools = [types.Tool(function_declarations=[
                    types.FunctionDeclaration(name=t.name, description=t.description, parameters=t.inputSchema)
                ]) for t in mcp_tools.tools]

                config = types.GenerateContentConfig(
                    system_instruction=(
                        f"Jsi Jarvis. Aktuální čas serveru je {current_time_info}. "
                        "Při plánování schůzek v češtině předpokládej, že časy jako 've 4' "
                        "znamenají 16:00 (odpoledne), pokud není jasné, že jde o ráno. "
                        "Vždy generuj časy ve formátu ISO 8601 (např. 2026-04-03T16:00:00Z)."
                    ),
                    tools=gemini_tools,
                    temperature=0.5
                )


                chat = self.client.chats.create(model="gemini-2.5-flash", config=config, history=gemini_history)
                response = chat.send_message(user_message)


                while response.function_calls:
                    tool_responses = []
                    for call in response.function_calls:
                        args_dict = dict(call.args) if call.args else {}
                        try:
                            mcp_result = await session.call_tool(call.name, arguments=args_dict)
                            result_text = mcp_result.content[0].text if mcp_result.content else "Provedeno."
                        except Exception as e:
                            result_text = f"Chyba: {e}"

                        tool_responses.append(
                            types.Part.from_function_response(name=call.name, response={"result": result_text}))
                    response = chat.send_message(tool_responses)

                bot_reply = response.text


                new_title = None
                if chat_id:
                    msg_count = chat_manager.save_message(chat_id, "user", user_message)
                    chat_manager.save_message(chat_id, "bot", bot_reply)
                    if msg_count == 1:
                        new_title = self._generate_title(user_message)
                        chat_manager.update_title(chat_id, new_title)

                return {"reply": bot_reply, "new_title": new_title}

"""if __name__ == "__main__":
    async def main():
        agent = JarvisAgent()

        # Zkusíme něco, co vyžaduje kalendář
        odpoved = await agent.process_message("Co mám naplánováno v kalendáři?")
        print("\n=== FINÁLNÍ ODPOVĚĎ ===")
        print(odpoved)


    asyncio.run(main())
    """
