from datetime import datetime

import httpx

from pytonconnect.exceptions import FetchWalletsError
from pytonconnect.logger import _LOGGER


FALLBACK_WALLETS_LIST = [
    {
        "app_name": "telegram-wallet",
        "name": "Wallet",
        "image": "https://wallet.tg/images/logo-288.png",
        "about_url": "https://wallet.tg/",
        "universal_url": "https://t.me/wallet?attach=wallet",
        "bridge": [
            {
                "type": "sse",
                "url": "https://bridge.tonapi.io/bridge"
            }
        ],
        "platforms": ["ios", "android", "macos", "windows", "linux"]
    },
    {
        "name": "Tonkeeper",
        "image": "https://tonkeeper.com/assets/tonconnect-icon.png",
        "tondns": "tonkeeper.ton",
        "about_url": "https://tonkeeper.com",
        "universal_url": "https://app.tonkeeper.com/ton-connect",
        "bridge": [
            {
                "type": "sse",
                "url": "https://bridge.tonapi.io/bridge"
            },
            {
                "type": "js",
                "key": "tonkeeper"
            }
        ]
    },
    {
        "name": "Tonhub",
        "image": "https://tonhub.com/tonconnect_logo.png",
        "about_url": "https://tonhub.com",
        "universal_url": "https://tonhub.com/ton-connect",
        "bridge": [
            {
                "type": "js",
                "key": "tonhub"
            },
            {
                "type": "sse",
                "url": "https://connect.tonhubapi.com/tonconnect"
            }
        ]
    }
]


class WalletsListManager:

    _wallets_list_source = 'https://raw.githubusercontent.com/ton-blockchain/wallets-list/main/wallets-v2.json'
    _cache_ttl: int

    _wallets_list_cache: dict
    _wallets_list_cache_creation_timestamp: int

    def __init__(self, wallets_list_source=None, cache_ttl=None):
        if wallets_list_source:
            self._wallets_list_source = wallets_list_source
        self._cache_ttl = cache_ttl

        self._wallets_list_cache = None
        self._wallets_list_cache_creation_timestamp = None

    def get_wallets(self):
        if self._cache_ttl \
                and self._wallets_list_cache_creation_timestamp \
                and int(datetime.now().timestamp()) > self._wallets_list_cache_creation_timestamp + self._cache_ttl:
            self._wallets_list_cache = None

        if not self._wallets_list_cache:
            wallets_list = None
            try:
                wallets_list = httpx.get(self._wallets_list_source).json()
                if not isinstance(wallets_list, list):
                    raise FetchWalletsError('Wrong wallets list format, wallets list must be an array.')

            except Exception as e:
                _LOGGER.error(f'WalletsListManager get_wallets {type(e)}: {e}')
                wallets_list = FALLBACK_WALLETS_LIST

            self._wallets_list_cache = []
            for wallet in wallets_list:
                supported_wallet = self._get_supported_wallet_config(wallet)
                if supported_wallet:
                    self._wallets_list_cache.append(supported_wallet)

            self._wallets_list_cache_creation_timestamp = int(datetime.now().timestamp())

        return self._wallets_list_cache

    def _get_supported_wallet_config(self, wallet):
        if not isinstance(wallet, dict):
            _LOGGER.warning(f'Not supported wallet: is not a dict -> {wallet}')
            return None

        containsName = 'name' in wallet
        containsImage = 'image' in wallet
        containsAbout = 'about_url' in wallet

        if not containsName or not containsImage or not containsAbout:
            _LOGGER.warning(f'Not supported wallet: contains -> name({containsName}), image({containsImage}), '
                            f'about({containsAbout}), config -> {wallet}')
            return None

        if 'bridge' not in wallet or not isinstance(wallet['bridge'], list) or not len(wallet['bridge']):
            _LOGGER.warning(f'Not supported wallet: bridge is not a list or len is equal 0, config -> {wallet}')
            return None

        walletConfig = {
            'name': wallet['name'],
            'image': wallet['image'],
            'about_url': wallet['about_url'],
            'app_name': wallet.get('app_name')
        }

        for bridge in wallet['bridge']:
            if bridge['type'] == 'sse':
                if 'url' not in bridge:
                    _LOGGER.warning(f'Not supported wallet: bridge url not found, config -> {wallet}')
                    return None

                walletConfig['bridge_url'] = bridge['url']
                if 'universal_url' in wallet:
                    walletConfig['universal_url'] = wallet['universal_url']
                break

        if 'bridge_url' not in walletConfig:
            _LOGGER.warning(f'Not supported wallet: sse not found, config -> {wallet}')
            return None

        return walletConfig


if __name__ == '__main__':
    wallets_list = WalletsListManager()
    print('Supported list of wallets:', wallets_list.get_wallets())
