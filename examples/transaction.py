"""
Given example shows how to deserialize returned 
Bag of Cells (BoC) from transaction

It requires installation of the `pytoniq_core` python package
and Tonkeeper app
"""

import asyncio
import logging
from datetime import datetime

from pytoniq_core.boc import Cell

from pytonconnect import TonConnect
from pytonconnect.exceptions import UserRejectsError

logging.basicConfig(level=logging.DEBUG)


async def _main():
    connector = TonConnect(
        manifest_url="https://raw.githubusercontent.com/XaBbl4/pytonconnect/main/pytonconnect-manifest.json"
    )
    is_connected = await connector.restore_connection()

    def status_changed(wallet_info):
        print(f"{wallet_info=}")

    def status_error(e):
        print(f"Got connector error: {e}")

    connector.on_status_change(status_changed, status_error)

    if not is_connected:
        print("Connection wasn't resotred. Connecting to the Tonkeeper")
        wallets_list = connector.get_wallets()
        generated_url = await connector.connect(wallets_list[1])
        print(f"Open to connect your wallet: {generated_url}")
    else:
        print("Connection successfully restored")

    print("Waiting 2 minutes to connect...")
    for _ in range(120):
        await asyncio.sleep(1)
        if connector.connected and connector.account and connector.account.address:
            print(f"Connected with {connector.account.address}")
            break
    else:
        raise Exception("Failed to connect wallet")

    await asyncio.sleep(1)

    transaction = {
        "valid_until": int(datetime.now().timestamp()) + 900,
        "messages": [
            {
                "address": "0:0000000000000000000000000000000000000000000000000000000000000000",
                "amount": "1",
            },
            {
                "address": "0:0000000000000000000000000000000000000000000000000000000000000000",
                "amount": "1",
            },
        ],
    }

    try:
        print("Sending transaction...")
        result = await connector.send_transaction(transaction)
        print("Transaction was sent successfully")

    except UserRejectsError:
        raise Exception("You rejected the transaction")

    finally:
        print("Waiting 2 minutes to disconnect...")
        asyncio.create_task(connector.disconnect())
        for _ in range(120):
            await asyncio.sleep(1)
            if not connector.connected:
                print("Disconnected")
                break
        print("App is closed")

    await asyncio.sleep(1)

    # `msg_hash` could be used to get transaction info from Ton API
    msg_hash = Cell.one_from_boc(result["boc"]).hash.hex()
    print(f"Transaction info -> https://toncenter.com/api/v3/transactionsByMessage?direction=out&msg_hash={msg_hash}&limit=128&offset=0")
    print("Done")


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
