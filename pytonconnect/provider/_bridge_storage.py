import json
from hashlib import sha256

from pytonconnect.storage import IStorage


class BridgeProviderStorage:

    _storage: IStorage

    @property
    def storage(self):
        return self._storage

    def __init__(self, storage: IStorage):
        self._storage = storage

    async def setConnection(self, connection: dict):
        await self._storage.set_item(IStorage.KEY_CONNECTION,
                                     json.dumps(connection, indent=2))

    async def removeConnection(self):
        await self._storage.remove_item(IStorage.KEY_CONNECTION)

    async def getConnection(self) -> dict:
        return json.loads(await self._storage.get_item(IStorage.KEY_CONNECTION, "{}"))

    async def setLastWalletEventId(self, event_id: int):
        connection = await self.getConnection()
        if connection and 'connect_event' in connection:
            connection['last_wallet_event_id'] = str(event_id)
            await self.setConnection(connection)

    async def getLastWalletEventId(self):
        connection = await self.getConnection()
        return connection['last_wallet_event_id'] if 'last_wallet_event_id' in connection else 0

    async def increaseNextRpcRequestId(self):
        connection = await self.getConnection()
        if connection and 'next_rpc_request_id' in connection:
            req_id = connection.get('next_rpc_request_id', '0')
            connection['next_rpc_request_id'] = str(int(req_id) + 1)
            await self.setConnection(connection)
            return req_id


class BridgeGatewayStorage:

    _storage: IStorage
    __key_last_event_id: str

    @property
    def storage(self):
        return self._storage

    def __init__(self, provider_storage: BridgeProviderStorage, bridge_url: str):
        bridge_url = sha256(bridge_url.encode()).hexdigest()[:6]
        self._storage = provider_storage.storage
        self.__key_last_event_id = f'{IStorage.KEY_LAST_EVENT_ID}:{bridge_url}'

    async def setLastEventId(self, last_event_id: str):
        await self._storage.set_item(self.__key_last_event_id, last_event_id)

    async def removeLastEventId(self):
        await self._storage.remove_item(self.__key_last_event_id)

    async def getLastEventId(self):
        last_event_id = await self._storage.get_item(self.__key_last_event_id)
        if last_event_id is None:
            last_event_id = await self._storage.get_item(IStorage.KEY_LAST_EVENT_ID)
        return last_event_id
