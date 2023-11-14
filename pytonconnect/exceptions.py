
class TonConnectError(Exception):
    prefix = '[TON_CONNECT_SDK_ERROR]'
    info = None

    def __init__(self, message=None):
        super(TonConnectError, self).__init__(f'{self.prefix}'
                                              + (f': {self.info}' if self.info else '')
                                              + (f' {message}' if message is not None else '')
                                              )


class WalletAlreadyConnectedError(TonConnectError):
    info = ('Wallet connection called but wallet already connected. '
            'To avoid the error, disconnect the wallet before doing a new connection.')


class WalletNotConnectedError(TonConnectError):
    info = 'Send transaction or other protocol methods called while wallet is not connected.'


class WalletNotSupportFeatureError(TonConnectError):
    info = "Wallet doesn't support requested feature method."


class FetchWalletsError(TonConnectError):
    info = 'An error occurred while fetching the wallets list.'


class UnknownError(TonConnectError):
    info = 'Unknown error.'


class BadRequestError(TonConnectError):
    info = 'Request to the wallet contains errors.'


class UnknownAppError(TonConnectError):
    info = 'App tries to send rpc request to the injected wallet while not connected.'


class UserRejectsError(TonConnectError):
    info = 'User rejects the action in the wallet.'


class ManifestNotFoundError(TonConnectError):
    info = ('Manifest not found. Make sure you added `tonconnect-manifest.json` to the root of your app '
            'or passed correct manifest_url. '
            'See more https://github.com/ton-connect/docs/blob/main/requests-responses.md#app-manifest')


class ManifestContentError(TonConnectError):
    info = ('Passed `tonconnect-manifest.json` contains errors. Check format of your manifest. '
            'See more https://github.com/ton-connect/docs/blob/main/requests-responses.md#app-manifest')
