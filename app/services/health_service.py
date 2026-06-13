import asyncio
from urllib.parse import urlparse

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine


async def check_database() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis() -> bool:
    settings = get_settings()
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    password = parsed.password
    database = int((parsed.path or "/0").lstrip("/") or 0)
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2)
        if password:
            await _redis_command(reader, writer, "AUTH", password)
        if database:
            await _redis_command(reader, writer, "SELECT", str(database))
        response = await _redis_command(reader, writer, "PING")
        writer.close()
        await writer.wait_closed()
        return response == b"+PONG\r\n"
    except Exception:
        return False


async def _redis_command(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *parts: str,
) -> bytes:
    encoded = [part.encode("utf-8") for part in parts]
    payload = f"*{len(encoded)}\r\n".encode("ascii")
    for part in encoded:
        payload += f"${len(part)}\r\n".encode("ascii") + part + b"\r\n"
    writer.write(payload)
    await writer.drain()
    return await asyncio.wait_for(reader.readline(), timeout=2)
