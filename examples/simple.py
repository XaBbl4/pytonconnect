import asyncio
from datetime import datetime


from pytonconnect import TonConnect
from pytonconnect.exceptions import UserRejectsError


async def main():
    connector = TonConnect(manifest_url='https://raw.githubusercontent.com/XaBbl4/pytonconnect/main/pytonconnect-manifest.json')
    is_connected = await connector.restore_connection()
    print('is_connected:', is_connected)

    def status_changed(wallet_info):
        print('wallet_info:', wallet_info)
        unsubscribe()

    def status_error(e):
        print('connect_error:', e)

    unsubscribe = connector.on_status_change(status_changed, status_error)

    wallets_list = connector.get_wallets()
    print('wallets_list:', wallets_list)
    
    generated_url = await connector.connect(wallets_list[0])
    print('generated_url:', generated_url)

    print('Waiting 2 minutes to connect...')
    for i in range(120):
        await asyncio.sleep(1)
        if connector.connected:
            if connector.account.address:
                print('Connected with address:', connector.account.address)
            break

    if connector.connected:
        print('Sending transaction...')

        transaction = {
            'valid_until': int(datetime.now().timestamp()) + 900,
            'messages': [
                {
                    'address': '0:0000000000000000000000000000000000000000000000000000000000000000',
                    'amount': '1',
                },
                {
                    'address': '0:0000000000000000000000000000000000000000000000000000000000000000',
                    'amount': '1',
                }
            ]
        }

        try:
            result = await connector.send_transaction(transaction)
            print('Transaction was sent successfully')
            print(result)

        except Exception as e:
            if isinstance(e, UserRejectsError):
                print('You rejected the transaction')
            else:
                print('Unknown error:', e)

        print('Waiting 2 minutes to disconnect...')
        asyncio.create_task(connector.disconnect())
        for i in range(120):
            await asyncio.sleep(1)
            if not connector.connected:
                print('Disconnected')
                break

    print('App is closed')


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
