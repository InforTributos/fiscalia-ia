import json
import logging
from typing import Any

import httpx
from config import settings
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self):
        self._url = settings.mcp_server_url
        self._token_url = settings.mcp_token_url
        self._user = settings.mcp_db_user
        self._password = settings.mcp_db_password
        self._timeout = settings.mcp_timeout

    async def _get_token(self) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._token_url,
                data={"grant_type": "password", "username": self._user, "password": self._password},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        timeout = httpx.Timeout(self._timeout, read=self._timeout)

        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            async with streamable_http_client(self._url, http_client=client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments=arguments or {})
                    if not result.content:
                        return {}
                    text = result.content[0].text
                    return json.loads(text) if isinstance(text, str) else text

    async def close(self):
        pass
