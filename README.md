# PyTonConnect

[![PyPI](https://img.shields.io/pypi/v/pytonconnect?color=blue)](https://pypi.org/project/pytonconnect/)

Python SDK for TON Connect 2.0

Analogue of the [@tonconnect/sdk](https://github.com/ton-connect/sdk/tree/main/packages/sdk) library.

Use it to connect your app to TON wallets via TonConnect protocol. You can find more details and the protocol specification in the [docs](https://github.com/ton-connect/docs).

# Installation

Install Python 3 package: `pip3 install pytonconnect`

# Examples
## Add the tonconnect-manifest

App needs to have its manifest to pass meta information to the wallet. Manifest is a JSON file named as `tonconnect-manifest.json` following format:

```json
{
  "url": "<app-url>",                        // required
  "name": "<app-name>",                      // required
  "iconUrl": "<app-icon-url>",               // required
  "termsOfUseUrl": "<terms-of-use-url>",     // optional
  "privacyPolicyUrl": "<privacy-policy-url>" // optional
}
```

Make sure that manifest is available to GET by its URL.

## Init connector and call `restore_connection`.

If user connected his wallet before, connector will restore the connection

```python
import asyncio
from pytonconnect import TonConnect

async def main():
    connector = TonConnect(manifest_url='https://raw.githubusercontent.com/XaBbl4/pytonconnect/main/pytonconnect-manifest.json')
    is_connected = await connector.restore_connection()
    print('is_connected:', is_connected)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
```

## Fetch wallets list

You can fetch all supported wallets list

```python
wallets_list = connector.get_wallets()

# wallets_list is 
# [
#   {
#     name: str,
#     image: str,
#     about_url: str,
#     bridge_url: str,
#     universal_url: str,
#   },
# ]
```

You also can get wallets list using `get_wallets` static method:
```python
wallets_list = TonConnect.get_wallets()
```

## Subscribe to the connection status changes

```python
def status_changed(wallet_info):
    # update state/reactive variables to show updates in the ui
    print('wallet_info:', wallet_info)
    unsubscribe()

unsubscribe = connector.on_status_change(status_changed)
# call unsubscribe() later to save resources when you don't need to listen for updates anymore.
```

## Initialize a wallet connection via universal link
```python
generated_url = await connector.connect(wallets_list[0])
print('generated_url:', generated_url)
```

Then you have to show this link to user as QR-code, or use it as a deep_link. You will receive an update in `connector.on_status_change` when user approves connection in the wallet.

## Send transaction

```python
transaction = {
    'valid_until': 1681223913000,
    'messages': [
        {
            'address': '0:0000000000000000000000000000000000000000000000000000000000000000',
            'amount': '1',
            # 'stateInit': 'base64_YOUR_STATE_INIT' # just for instance. Replace with your transaction state_init or remove
        },
        {
            'address': '0:0000000000000000000000000000000000000000000000000000000000000000',
            'amount': '1',
            # 'payload': 'base64_YOUR_PAYLOAD' # just for instance. Replace with your transaction payload or remove
        }
    ]
}

try:
    result = await connector.send_transaction(transaction)
    print('Transaction was sent successfully')
except Exception as e:
    if isintance(e, UserRejectsError):
        print('You rejected the transaction. Please confirm it to send to the blockchain')
    else:
        print('Unknown error:', e)
```
