import asyncio
from tonsdk.utils import Address

from pytonconnect import TonConnect
from pytonconnect.storage import FileStorage
from pytonconnect.exceptions import TonConnectError


async def main():
    storage = FileStorage('connection_data.json')

    connector = TonConnect(manifest_url='https://raw.githubusercontent.com/XaBbl4/pytonconnect/main/pytonconnect-manifest.json', storage=storage)
    is_connected = await connector.restore_connection()
    print('is_connected:', is_connected)

    if not is_connected:
        wallets_list = connector.get_wallets()
        print('wallets_list:', wallets_list)
    
        generated_url = await connector.connect(wallets_list[0])
        print('generated_url:', generated_url)

    result = await connector.wait_for_connection()
    if isinstance(result, TonConnectError):
        print('error:', result)
    else:
        print('wallet_info:', result)
        if connector.connected and connector.account.address:
            print('Connected with address:', Address(connector.account.address).to_string(True, True, True))

    print('App is closed')


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
