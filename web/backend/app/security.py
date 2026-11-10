"""Limite de corpo, limite de requisições e cabeçalhos defensivos."""
from collections import deque
import json
import threading
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _TooLarge(Exception):
    pass


class BodySizeLimit:
    """Conta bytes recebidos; não confia somente em Content-Length."""

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        declared = dict(scope['headers']).get(b'content-length')
        if declared and declared.isdigit() and int(declared) > self.max_bytes:
            return await self._reject(send)
        total = 0

        async def counted() -> Message:
            nonlocal total
            message = await receive()
            if message['type'] == 'http.request':
                total += len(message.get('body', b''))
                if total > self.max_bytes:
                    raise _TooLarge
            return message
        try:
            await self.app(scope, counted, send)
        except _TooLarge:
            await self._reject(send)

    async def _reject(self, send: Send):
        body = json.dumps({'status': 'requisicao_grande', 'mensagem': 'Requisição maior que o permitido.'},
                          ensure_ascii=False).encode()
        await send({'type': 'http.response.start', 'status': 413,
                    'headers': [(b'content-type', b'application/json'),
                                (b'content-length', str(len(body)).encode())]})
        await send({'type': 'http.response.body', 'body': body})


class RateLimiter:
    """Janela deslizante em memória, por IP e por processo; não persiste entradas."""
    MAX_CLIENTS = 10_000

    def __init__(self, per_minute: int, clock=time.monotonic):
        self.limit, self.clock = per_minute, clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, client: str) -> int | None:
        """Registra a chamada; devolve segundos de espera se o limite estourou."""
        now = self.clock()
        with self._lock:
            if len(self._hits) >= self.MAX_CLIENTS and client not in self._hits:
                self._hits = {k: q for k, q in self._hits.items() if q and q[-1] > now-60}
                if len(self._hits) >= self.MAX_CLIENTS:
                    return 60
            hits = self._hits.setdefault(client, deque())
            while hits and hits[0] <= now-60:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, int(hits[0]+60-now)+1)
            hits.append(now)
            return None


SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                                "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"),
}
