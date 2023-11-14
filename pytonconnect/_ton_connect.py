import asyncio

from pytonconnect.exceptions import (
    ManifestContentError,
    ManifestNotFoundError,
    WalletAlreadyConnectedError,
    WalletNotConnectedError,
    WalletNotSupportFeatureError,
)
from pytonconnect.logger import _LOGGER
from pytonconnect.parsers import SendTransactionParser, ConnectEventParser, WalletInfo
from pytonconnect.provider import BridgeProvider
from pytonconnect.storage import IStorage, DefaultStorage

from ._wallets_list_manager import WalletsListManager


class TonConnect:

    _wallets_list = WalletsListManager()

    _provider: BridgeProvider
    _manifest_url: str
    _storage: IStorage

    _wallet: WalletInfo

    _status_change_subscriptions: list
    _status_change_error_subscriptions: list

    @property
    def connected(self):
        """Shows if the wallet is connected right now."""
        return self._wallet is not None

    @property
    def account(self):
        """Current connected account or None if no account is connected."""
        return self._wallet.account if self.connected else None

    @property
    def wallet(self):
        """Current connected wallet or None if no account is connected."""
        return self._wallet

    def __init__(
        self,
        manifest_url: str,
        storage: IStorage = DefaultStorage(),
        wallets_list_source: str = None,
        wallets_list_cache_ttl: int = None
    ):
        if wallets_list_source is not None or wallets_list_cache_ttl is not None:
            self._wallets_list = WalletsListManager(
                wallets_list_source=wallets_list_source,
                cache_ttl=wallets_list_cache_ttl)

        self._provider = None
        self._manifest_url = manifest_url
        self._storage = storage

        self._wallet = None

        self._status_change_subscriptions = []
        self._status_change_error_subscriptions = []

    def get_wallets(self=None):
        """Return available wallets list."""
        return TonConnect._wallets_list.get_wallets() if self is None else self._wallets_list.get_wallets()

    def on_status_change(self, callback, errors_handler=None):
        """Allows to subscribe to connection status changes and handle connection errors.

        :param callback: will be called after connections status changes with actual wallet or None
        :param errors_handler: will be called with some instance of TonConnectError when connect error is received
        :return: unsubscribe callback
        """
        self._status_change_subscriptions.append(callback)
        if errors_handler is not None:
            self._status_change_error_subscriptions.append(errors_handler)

        def unsubscribe():
            if callback in self._status_change_subscriptions:
                self._status_change_subscriptions.remove(callback)
            if errors_handler is not None and errors_handler in self._status_change_error_subscriptions:
                self._status_change_error_subscriptions.remove(errors_handler)

        return unsubscribe

    async def connect(self, wallet, request=None):
        """Generates universal link for an external wallet and subscribes to the wallet's bridge,
        or sends connect request to the injected wallet.

        :param wallet: wallet's bridge url and universal link for an external wallet.
        :param request: additional request to pass to the wallet while connect (currently only ton_proof is available).
        :return: universal link if external wallet was passed.
        """
        if self.connected:
            raise WalletAlreadyConnectedError()

        if self._provider:
            self._provider.close_connection()

        self._provider = self._create_provider(wallet)

        return await self._provider.connect(self._create_connect_request(request))

    async def restore_connection(self):
        """Try to restore existing session and reconnect to the corresponding wallet.
        Call it immediately when your app is loaded.

        :return: True if connection is restored
        """
        try:
            self._provider = BridgeProvider(self._storage)
        except Exception:
            await self._storage.remove_item(IStorage.KEY_CONNECTION)
            self._provider = None

        if not self._provider:
            return False

        self._provider.listen(self._wallet_events_listener)
        return await self._provider.restore_connection()

    async def send_transaction(self, transaction: dict) -> dict:
        """Asks connected wallet to sign and send the transaction.

        :param transaction: transaction to send.
        :return: signed transaction boc that allows you to find the transaction in the blockchain.
        If user rejects transaction, method will throw the corresponding error.
        """
        if not self.connected:
            raise WalletNotConnectedError()

        options = {'required_messages_number': len(transaction.get('messages', []))}
        self._check_send_transaction_support(self._wallet.device.features, options)

        request = {
            'valid_until': transaction.get('valid_until', None),
            'from': transaction.get('from', self._wallet.account.address),
            'network': transaction.get('network', self._wallet.account.chain),
            'messages': transaction.get('messages', [])
        }

        response = await self._provider.send_request(SendTransactionParser.convert_to_rpc_request(request))

        if SendTransactionParser.is_error(response):
            return SendTransactionParser.parse_and_throw_error(response)

        return SendTransactionParser.convert_from_rpc_response(response)

    async def disconnect(self):
        """Disconnect from wallet and drop current session."""
        if not self.connected:
            raise WalletNotConnectedError()

        await self._provider.disconnect()
        self._on_wallet_disconnected()

    def pause_connection(self):
        """Pause bridge HTTP connection.
        Might be helpful, if you use SDK on backend and want to save server resources.
        """
        self._provider.pause()

    async def unpause_connection(self):
        """Unpause bridge HTTP connection if it is paused."""
        await self._provider.unpause()

    def wait_for_connection(self):
        wait_resolve = asyncio.get_running_loop().create_future()
        if self.connected:
            wait_resolve.set_result(self.wallet)
            return wait_resolve

        def status_changed(wallet_info):
            wait_resolve.set_result(wallet_info)
            unsubscribe()

        def status_error(e):
            wait_resolve.set_result(e)
            unsubscribe()

        unsubscribe = self.on_status_change(status_changed, status_error)

        return wait_resolve

    def _check_send_transaction_support(self, features, options):
        supports_deprecated_send_transaction_feature = 'SendTransaction' in features
        send_transaction_feature = None
        for feature in features:
            if isinstance(feature, dict) and feature.get('name', None) == 'SendTransaction':
                send_transaction_feature = feature
                break

        if not supports_deprecated_send_transaction_feature and not send_transaction_feature:
            raise WalletNotSupportFeatureError("Wallet doesn't support SendTransaction feature.")

        if send_transaction_feature:
            max_messages = send_transaction_feature.get('maxMessages', None)
            required_messages = options.get('required_messages_number')
            if max_messages and max_messages < required_messages:
                raise WalletNotSupportFeatureError(
                    'Wallet is not able to handle such SendTransaction request. '
                    f'Max support messages number is {max_messages}, but {required_messages} is required.')
        else:
            _LOGGER.warning("Connected wallet didn't provide information about max allowed messages "
                            "in the SendTransaction request. Request may be rejected by the wallet.")

    def _create_provider(self, wallet: dict) -> BridgeProvider:
        provider = BridgeProvider(self._storage, wallet)
        provider.listen(self._wallet_events_listener)
        return provider

    def _wallet_events_listener(self, data):
        if data['event'] == 'connect':
            self._on_wallet_connected(data['payload'])

        elif data['event'] == 'connect_error':
            self._on_wallet_connect_error(data['payload'])

        elif data['event'] == 'disconnect':
            self._on_wallet_disconnected()

    def _on_wallet_connected(self, payload):
        self._wallet = ConnectEventParser.parse_response(payload)
        for listener in self._status_change_subscriptions:
            listener(self._wallet)

    def _on_wallet_connect_error(self, payload):
        _LOGGER.debug('connect error %s', payload)
        error = ConnectEventParser.parse_error(payload)
        for listener in self._status_change_error_subscriptions:
            listener(error)

        if isinstance(error, ManifestNotFoundError) or isinstance(error, ManifestContentError):
            _LOGGER.exception(error)
            raise error

    def _on_wallet_disconnected(self):
        self._wallet = None
        for listener in self._status_change_subscriptions:
            listener(None)

    def _create_connect_request(self, request):
        items = [
            {
                'name': 'ton_addr'
            }
        ]

        if isinstance(request, dict) and 'ton_proof' in request:
            items.append({
                'name': 'ton_proof',
                'payload': request['ton_proof']
            })

        return {
            'manifestUrl': self._manifest_url,
            'items': items
        }
