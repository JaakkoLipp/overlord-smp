"""Minimal Source RCON client (zero external dependencies).

The Source RCON protocol is a simple length-prefixed, little-endian packet
format. We keep our own implementation rather than pulling a dependency so the
bridge stays trivially auditable and portable.
"""
from __future__ import annotations

import logging
import socket
import struct
import threading

log = logging.getLogger("overlord.rcon")

_SERVERDATA_AUTH = 3
_SERVERDATA_AUTH_RESPONSE = 2
_SERVERDATA_EXECCOMMAND = 2
_SERVERDATA_RESPONSE_VALUE = 0


class RconError(RuntimeError):
    pass


class RconClient:
    """Synchronous RCON client with lazy connect and one-shot reconnect.

    Thread-safe at the command level: a lock serialises request/response pairs
    so the poll loop and the overlord dispatch can share one client.
    """

    def __init__(self, host: str, port: int, password: str, timeout: float = 5.0):
        self._host = host
        self._port = port
        self._password = password
        self._timeout = timeout
        self._sock: socket.socket | None = None
        self._req_id = 0
        self._lock = threading.Lock()

    # -- connection lifecycle -------------------------------------------------
    def connect(self) -> None:
        self.close()
        log.debug("connecting to %s:%s", self._host, self._port)
        self._sock = socket.create_connection((self._host, self._port), self._timeout)
        self._sock.settimeout(self._timeout)
        self._authenticate()
        log.info("RCON connected to %s:%s", self._host, self._port)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _authenticate(self) -> None:
        req_id = self._send(_SERVERDATA_AUTH, self._password)
        # Some servers send an empty RESPONSE_VALUE before the AUTH_RESPONSE.
        resp_id, _ = self._recv()
        if resp_id == -1:
            # try one more frame in case of the leading empty packet
            resp_id, _ = self._recv()
        if resp_id != req_id:
            raise RconError("RCON authentication failed (bad password?)")

    # -- packet I/O -----------------------------------------------------------
    def _send(self, ptype: int, body: str) -> int:
        assert self._sock is not None
        self._req_id += 1
        payload = struct.pack("<ii", self._req_id, ptype) + body.encode("utf-8") + b"\x00\x00"
        self._sock.sendall(struct.pack("<i", len(payload)) + payload)
        return self._req_id

    def _recv(self) -> tuple[int, str]:
        assert self._sock is not None
        raw_len = self._read_exact(4)
        (length,) = struct.unpack("<i", raw_len)
        data = self._read_exact(length)
        req_id, _ptype = struct.unpack("<ii", data[:8])
        body = data[8:-2].decode("utf-8", errors="replace")
        return req_id, body

    def _read_exact(self, n: int) -> bytes:
        assert self._sock is not None
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise RconError("RCON socket closed mid-read")
            buf += chunk
        return buf

    # -- public command -------------------------------------------------------
    def command(self, cmd: str) -> str:
        """Run a single command, reconnecting once on a dropped socket."""
        with self._lock:
            for attempt in (1, 2):
                try:
                    if self._sock is None:
                        self.connect()
                    req_id = self._send(_SERVERDATA_EXECCOMMAND, cmd)
                    resp_id, body = self._recv()
                    if resp_id != req_id:
                        log.warning("RCON response id mismatch (%s != %s)", resp_id, req_id)
                    return body
                except (OSError, RconError) as exc:
                    log.warning("RCON command failed (attempt %s): %s", attempt, exc)
                    self.close()
                    if attempt == 2:
                        raise RconError(f"RCON command failed: {cmd!r}") from exc
            return ""  # unreachable

    def __enter__(self) -> "RconClient":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
