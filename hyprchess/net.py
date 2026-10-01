"""Direct two-player online games: one side hosts a TCP port, the other joins it.

Messages are one JSON object per line. Everything received is untrusted and is
validated by the caller before it touches the game.
"""

import asyncio
import json
import socket

PORT = 28155
VERSION = 1


class Peer:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader, self.writer = reader, writer

    async def send(self, **msg) -> None:
        try:
            self.writer.write(json.dumps(msg).encode() + b"\n")
            await self.writer.drain()
        except OSError:
            pass  # the receive loop notices the dead connection

    async def recv(self) -> dict | None:
        """Next message, or None when the connection is gone or sends garbage."""
        try:
            line = await self.reader.readline()
            msg = json.loads(line) if line else None
        except (OSError, ValueError, asyncio.IncompleteReadError):  # ValueError: bad JSON or oversized line
            return None
        return msg if isinstance(msg, dict) and isinstance(msg.get("t"), str) else None

    def close(self) -> None:
        self.writer.close()


async def host(port: int, on_peer) -> asyncio.Server:
    """Listen for one opponent; `on_peer(Peer)` is called when they connect."""

    async def connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        on_peer(Peer(reader, writer))

    return await asyncio.start_server(connected, "0.0.0.0", port)


async def join(address: str, timeout: float = 8.0) -> Peer:
    """Connect to `host` or `host:port`. Raises OSError/TimeoutError/ValueError on failure."""
    name, _, port = address.strip().rpartition(":") if ":" in address else (address.strip(), "", "")
    if not name:
        raise ValueError("enter an address like 192.168.1.20 or host:28155")
    reader, writer = await asyncio.wait_for(asyncio.open_connection(name, int(port or PORT)), timeout)
    return Peer(reader, writer)


def local_addresses() -> list[str]:
    """Addresses an opponent could use to reach this machine (best effort, sends nothing)."""
    found = []
    for target in ("10.255.255.255", "100.100.100.100"):  # LAN route, Tailscale route
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.connect((target, 1))
                found.append(s.getsockname()[0])
            except OSError:
                pass
    return list(dict.fromkeys(a for a in found if not a.startswith("127."))) or ["127.0.0.1"]


def valid_hello(msg: dict | None) -> bool:
    """Check the host's opening message before trusting its game settings."""
    if not msg or msg.get("t") != "hello" or msg.get("v") != VERSION:
        return False
    base, inc = msg.get("base"), msg.get("inc")
    ok_base = base is None or (type(base) is int and 10 <= base <= 6 * 3600)
    return msg.get("host_color") in ("white", "black") and ok_base and type(inc) is int and 0 <= inc <= 600
