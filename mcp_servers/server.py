# mcp_servers/google_workspace/server.py
from mcp.server.fastmcp import FastMCP

# Importujeme registrační funkce z našich modulů


from google_workspace.calendar_module import register_calendar
from google_workspace.drive_manager import register_drive
from google_workspace.gmail_manager import register_gmail

mcp = FastMCP("Jarvis Unified Server")

register_calendar(mcp)
register_drive(mcp)
register_gmail(mcp)

if __name__ == "__main__":
    mcp.run()