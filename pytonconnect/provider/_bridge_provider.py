import asyncio
import json
from typing import Dict
from urllib.parse import quote_plus

from pytonconnect.crypto import SessionCrypto
from pytonconnect.exceptions import TonConnectError
from pytonconnect.logger import _LOGGER
from pytonconnect.storage import IStorage

from ._provider import BaseProvider
from ._bridge_gateway import BridgeGateway
from ._bridge_session import BridgeSession


class BridgeProvider(BaseProvider):

    DISCONNECT_TIMEOUT = 600
    STANDART_UNIVERSAL_URL = 'tc://'

    _storage: IStorage
    _wallet: dict

    _session: BridgeSession
    _gateway: BridgeGateway
    _pending_requests: dict
    _listeners: list
    _api_tokens: Dict[str, str]

    def __init__(self, storage: IStorage, wallet: dict = None, api_tokens: Dict[str, str] = {}):
        self._storage = storage
        self._wallet = wallet

        self._session = BridgeSession()
        self._gateway = None
        self._pending_requests = {}
        self._listeners = []
        self._api_tokens = api_tokens

    async def connect(self, request: dict):
        self._close_gateways()
        session_crypto = SessionCrypto()

        bridge_url = ''
        universal_url = BridgeProvider.STANDART_UNIVERSAL_URL

        if isinstance(self._wallet, dict):
            bridge_url = self._wallet['bridge_url']
            if 'universal_url' in self._wallet:
                universal_url = self._wallet['universal_url']

            self._gateway = BridgeGateway(
                self._storage,
                bridge_url,
                session_crypto.session_id,
                self._gateway_listener,
                self._gateway_errors_listener,
                self._api_tokens,
            )

            await self._gateway.register_session()

        self._session.session_crypto = session_crypto
        self._session.bridge_url = bridge_url

        return self._generate_universal_url(universal_url, request)

    async def restore_connection(self):
        self._close_gateways()

        connection = await self._storage.get_item(IStorage.KEY_CONNECTION)
        if not connection:
            return False
        connection = json.loads(connection)

        if 'session' not in connection:
            return False
        self._session = BridgeSession(connection['session'])

        self._gateway = BridgeGateway(
            self._storage,
            self._session.bridge_url,
            self._session.session_crypto.session_id,
            self._gateway_listener,
            self._gateway_errors_listener,
            self._api_tokens,
        )

        await self._gateway.register_session()

        for listener in self._listeners:
            listener(connection['connect_event'])

        return True

    def close_connection(self):
        self._close_gateways()
        self._session = BridgeSession()
        self._gateway = None
        self._pending_requests = {}
        self._listeners = []

    async def disconnect(self):
        loop = asyncio.get_running_loop()
        resolve = loop.create_future()

        def on_request_sent(request_future: asyncio.Future):
            asyncio.create_task(self._remove_session()) \
                .add_done_callback(lambda x: resolve.set_result(True) if not resolve.done() else None)
            request_future.set_result(None)

        try:
            await asyncio.wait_for(self.send_request({'method': 'disconnect', 'params': []},
                                                     on_request_sent=on_request_sent),
                                   timeout=self.DISCONNECT_TIMEOUT)
        except Exception:
            _LOGGER.exception('Provider disconnect')
        finally:
            if not resolve.done():
                await self._remove_session()
                resolve.set_result(True)

        return await resolve

    def pause(self):
        if self._gateway is not None:
            self._gateway.pause()

    async def unpause(self):
        if self._gateway is not None:
            await self._gateway.unpause()

    async def send_request(self, request: dict, on_request_sent=None):
        if not self._gateway or not self._session or not self._session.wallet_public_key:
            raise TonConnectError('Trying to send bridge request without session.')

        connection = json.loads(await self._storage.get_item(IStorage.KEY_CONNECTION, '{}'))
        id = connection.get('next_rpc_request_id', '0')
        connection['next_rpc_request_id'] = str(int(id)+1)
        await self._storage.set_item(IStorage.KEY_CONNECTION, json.dumps(connection))

        request['id'] = id
        _LOGGER.debug(f'Provider send http-bridge request: {request}')

        encoded_request = self._session.session_crypto.encrypt(
            json.dumps(request),
            self._session.wallet_public_key
        )

        await self._gateway.send(encoded_request, self._session.wallet_public_key, request['method'])

        loop = asyncio.get_running_loop()
        resolve = loop.create_future()

        self._pending_requests[id] = resolve
        if on_request_sent is not None:
            on_request_sent(resolve)

        return await resolve

    def listen(self, callback):
        self._listeners.append(callback)

    async def _gateway_listener(self, bridge_incoming_message):
        wallet_message = json.loads(
            self._session.session_crypto.decrypt(bridge_incoming_message['message'], bridge_incoming_message['from'])
        )

        _LOGGER.debug(f'Wallet message received: {wallet_message}')

        if 'event' not in wallet_message:
            if 'id' in wallet_message:
                id = wallet_message['id']
                if id not in self._pending_requests:
                    _LOGGER.debug(f"Response id {id} doesn't match any request's id")
                    return

                self._pending_requests[id].set_result(wallet_message)
                del self._pending_requests[id]
            return

        if 'id' in wallet_message:
            id = int(wallet_message['id'])
            connection = json.loads(await self._storage.get_item(IStorage.KEY_CONNECTION, '{}'))
            last_id = connection['last_wallet_event_id'] if 'last_wallet_event_id' in connection else 0

            if last_id and id <= last_id:
                _LOGGER.error(
                    f'Received event id (={id}) must be greater than stored last wallet event id (={last_id})')
                return

            if 'event' in wallet_message and wallet_message['event'] != 'connect':
                connection['last_wallet_event_id'] = id
                await self._storage.set_item(IStorage.KEY_CONNECTION, json.dumps(connection))

        # self.listeners might be modified in the event handler
        listeners = self._listeners.copy()

        if wallet_message['event'] == 'connect':
            await self._update_session(wallet_message, bridge_incoming_message['from'])

        elif wallet_message['event'] == 'disconnect':
            await self._remove_session()

        for listener in listeners:
            listener(wallet_message)

    async def _gateway_errors_listener(self, e=None):
        raise TonConnectError(f'Bridge error {json.dumps(e or {})}')

    async def _update_session(self, connect_event: dict, wallet_public_key: str):
        self._session.wallet_public_key = wallet_public_key

        connection = {
            'type': 'http',
            'session': self._session.get_dict(),
            'last_wallet_event_id': connect_event['id'] if 'id' in connect_event else None,
            'connect_event': connect_event,
            'next_rpc_request_id': 0
        }

        await self._storage.set_item(IStorage.KEY_CONNECTION, json.dumps(connection))

    async def _remove_session(self):
        if self._gateway is not None:
            self.close_connection()
            await self._storage.remove_item(IStorage.KEY_CONNECTION)
            await self._storage.remove_item(IStorage.KEY_LAST_EVENT_ID)

    def _generate_universal_url(self, universal_url: str, request: dict):
        if 'tg://' in universal_url or 't.me/' in universal_url:
            return self._generate_tg_universal_url(universal_url, request)
        return self._generate_regular_universal_url(universal_url, request)

    def _generate_regular_universal_url(self, universal_url: str, request: dict):
        version = 2
        session_id = self._session.session_crypto.session_id
        request_safe = quote_plus(json.dumps(request, separators=(',', ':')))

        universal_base = universal_url.rstrip('/')
        url = f'{universal_base}?v={version}&id={session_id}&r={request_safe}'

        return url

    def _generate_tg_universal_url(self, universal_url: str, request: dict):
        link = self._generate_regular_universal_url('about:blank', request)
        link_params = link.split('?')[1]
        start_attach = ('tonconnect-' + link_params
                        .replace('.', '%2E')
                        .replace('-', '%2D')
                        .replace('_', '%5F')
                        .replace('&', '-')
                        .replace('=', '__')
                        .replace('%', '--')
                        .replace('+', '')
                        )

        return universal_url + '&startattach=' + start_attach

    def _close_gateways(self):
        if self._gateway:
            self._gateway.close()
