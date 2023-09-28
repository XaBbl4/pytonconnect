import asyncio
import json

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectionError
from aiohttp_sse_client import client as sse_client

from pytonconnect.exceptions import TonConnectError
from pytonconnect.logger import _LOGGER
from pytonconnect.storage import IStorage


class BridgeGateway:

    SSE_PATH = 'events'
    POST_PATH = 'message'
    DEFAULT_TTL = 300

    _handle_listen: asyncio.Task
    _event_source: sse_client.EventSource
    _is_closed: bool

    _storage: IStorage
    _bridge_url: str
    _session_id: str
    _listener: any
    _errors_listener: any


    def __init__(self, storage: IStorage, bridge_url: str, session_id: str, listener, errors_listener):

        self._handle_listen = None
        self._event_source = None
        self._is_closed = False

        self._storage = storage
        self._bridge_url = bridge_url
        self._session_id = session_id
        self._listener = listener
        self._errors_listener = errors_listener
    

    async def listen_event_source(self, resolve: asyncio.Future):
        try:
            async with self._event_source:
                resolve.set_result(True)
                async for event in self._event_source:
                    await self._messages_handler(event)

        except asyncio.exceptions.TimeoutError:
            _LOGGER.exception(f'Bridge error -> TimeoutError')
        except asyncio.exceptions.CancelledError:
            pass
        except ClientConnectionError:
            _LOGGER.exception(f'Bridge error -> ClientConnectionError')
        except Exception:
            _LOGGER.exception(f'Bridge error -> Unknown')
        
        if not resolve.done():
            resolve.set_result(False)


    async def register_session(self) -> bool:
        if self._is_closed:
            return False

        bridge_base = self._bridge_url.rstrip('/')
        bridge_url = f'{bridge_base}/{self.SSE_PATH}?client_id={self._session_id}'
        
        last_event_id = await self._storage.get_item(IStorage.KEY_LAST_EVENT_ID)
        if last_event_id:
            bridge_url += f'&last_event_id={last_event_id}'
        _LOGGER.debug(f'Bridge url -> {bridge_url}')

        if self._handle_listen is not None:
            self._handle_listen.cancel()

        loop = asyncio.get_running_loop()
        resolve = loop.create_future()

        self._event_source = sse_client.EventSource(bridge_url, timeout=-1, on_error=self._errors_handler)
        self._handle_listen = asyncio.create_task(self.listen_event_source(resolve))

        return await resolve


    async def send(self, request: str, receiver_public_key: str, topic: str, ttl: int = None):
        bridge_base = self._bridge_url.rstrip('/')
        bridge_url = f'{bridge_base}/{self.POST_PATH}?client_id={self._session_id}'
        bridge_url += f'&to={receiver_public_key}'
        bridge_url += f'&ttl={ttl if ttl else self.DEFAULT_TTL}'
        bridge_url += f'&topic={topic}'
        async with ClientSession() as session:
            async with session.post(bridge_url, data=request, headers={'Content-type': 'text/plain;charset=UTF-8'}):
                pass


    def pause(self):
        if self._handle_listen is not None:
            self._handle_listen.cancel()
            self._handle_listen = None


    async def unpause(self):
        await self.register_session()


    def close(self):
        self._is_closed = True
        self.pause()


    async def _messages_handler(self, event: sse_client.MessageEvent):
        await self._storage.set_item(IStorage.KEY_LAST_EVENT_ID, event.last_event_id)

        if not self._is_closed:
            try:
                bridge_incoming_message = json.loads(event.data)
            except:
                raise TonConnectError(f'Bridge message parse failed, message {event.data}')
            else:
                await self._listener(bridge_incoming_message)


    def _errors_handler(self):
        if not self._is_closed:
            if self._event_source.ready_state == sse_client.READY_STATE_CLOSED:
                _LOGGER.error('Bridge error -> READY_STATE_CLOSED')
                # TODO: reconnect
                return

            elif self._event_source.ready_state == sse_client.READY_STATE_CONNECTING:
                _LOGGER.error('Bridge error -> READY_STATE_CONNECTING')
                return
            
            if not self._errors_listener:
                self._errors_listener()
