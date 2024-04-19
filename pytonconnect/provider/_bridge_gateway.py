import asyncio
import json

from httpx import AsyncClient as ClientSession
from httpx_sse import EventSource, ServerSentEvent, aconnect_sse

from pytonconnect.exceptions import TonConnectError
from pytonconnect.logger import _LOGGER

from ._bridge_storage import BridgeGatewayStorage, BridgeProviderStorage


class BridgeGateway:

    SSE_PATH = 'events'
    POST_PATH = 'message'
    HEARTBEAT_MSG = 'heartbeat'
    DEFAULT_TTL = 300

    _handle_listen: asyncio.Task
    _event_source: EventSource
    _is_closed: bool

    _storage: BridgeGatewayStorage
    _bridge_url: str
    _session_id: str
    _listener: any
    _errors_listener: any

    def __init__(self, storage: BridgeProviderStorage, bridge_url: str, session_id: str, listener, errors_listener):

        self._handle_listen = None
        self._event_source = None
        self._is_closed = False

        self._storage = BridgeGatewayStorage(storage, bridge_url)
        self._bridge_url = bridge_url
        self._session_id = session_id
        self._listener = listener
        self._errors_listener = errors_listener

    async def listen_event_source(self, resolve: asyncio.Future, url: str, timeout):
        try:
            async with ClientSession() as client:
                async with aconnect_sse(client, "GET", url, timeout=timeout) as self._event_source:
                    resolve.set_result(True)
                    async for event in self._event_source.aiter_sse():
                        await self._messages_handler(event)

        except asyncio.exceptions.TimeoutError:
            _LOGGER.error('Bridge error -> TimeoutError')
            self.close()

        except asyncio.exceptions.CancelledError:
            pass

        except Exception:
            _LOGGER.exception('Bridge error -> Exception')
            if self._event_source.response.is_closed:
                await self.register_session()
            elif not self._errors_listener:
                self._errors_listener()

        if not resolve.done():
            resolve.set_result(False)

    async def register_session(self, timeout=5) -> bool:
        if self._is_closed:
            return False

        bridge_base = self._bridge_url.rstrip('/')
        bridge_url = f'{bridge_base}/{self.SSE_PATH}?client_id={self._session_id}'

        last_event_id = await self._storage.getLastEventId()
        if last_event_id:
            bridge_url += f'&last_event_id={last_event_id}'
        _LOGGER.debug(f'Bridge url -> {bridge_url}')

        loop = asyncio.get_running_loop()
        resolve = loop.create_future()

        self._handle_listen = asyncio.create_task(self.listen_event_source(resolve, bridge_url, timeout))

        return await resolve

    async def send(self, request: str, receiver_public_key: str, topic: str, ttl: int = None):
        bridge_base = self._bridge_url.rstrip('/')
        bridge_url = f'{bridge_base}/{self.POST_PATH}?client_id={self._session_id}'
        bridge_url += f'&to={receiver_public_key}'
        bridge_url += f'&ttl={ttl if ttl else self.DEFAULT_TTL}'
        bridge_url += f'&topic={topic}'
        async with ClientSession() as session:
            await session.post(bridge_url, data=request, headers={'Content-type': 'text/plain;charset=UTF-8'}):

    def pause(self):
        if self._handle_listen is not None:
            self._handle_listen.cancel()
            self._handle_listen = None

    async def unpause(self):
        await self.register_session()

    def close(self):
        self._is_closed = True
        self.pause()

    async def _messages_handler(self, event: ServerSentEvent):
        if event.event == self.HEARTBEAT_MSG:
            return

        await self._storage.setLastEventId(event.id)

        if not self._is_closed:
            try:
                bridge_incoming_message = json.loads(event.data)
            except Exception:
                raise TonConnectError(f'Bridge message parse failed, message {event.data}')
            else:
                await self._listener(bridge_incoming_message)
