import logging
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self, command: str = "python", args: list[str] | None = None):
        self.server_params = StdioServerParameters(
            command=command,
            args=args or [],
        )
        self._session: ClientSession | None = None

    async def connect(self):
        if self._session is None:
            self._read, self._write = await stdio_client(self.server_params).__aenter__()
            self._session = await ClientSession(self._read, self._write).__aenter__()
            await self._session.initialize()
            logger.info("MCP Client conectado exitosamente")

    async def disconnect(self):
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None
            logger.info("MCP Client desconectado")

    async def list_tools(self) -> list[dict]:
        await self.connect()
        result = await self._session.list_tools()
        return [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in result.tools]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict:
        await self.connect()
        result = await self._session.call_tool(name, arguments=arguments or {})
        return result.content[0].text if result.content else {}
