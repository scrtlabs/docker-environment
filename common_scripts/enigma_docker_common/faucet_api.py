import time
import socket
from urllib.parse import urlparse
import requests
from .logger import get_logger

logger = get_logger('eng_common.faucet')


def _wait_till_open(url, timeout: int = 60) -> None:
    p = urlparse(url)
    hostname = p.hostname
    port = p.port

    def is_ready():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((hostname, port))
        return result == 0

    for _ in range(timeout):
        if is_ready():
            return
        time.sleep(1)
    raise ConnectionError(f'Timeout waiting for {url}')


def request_coins(faucet_url, account: str, currency: str) -> float:
    """ Issue a requests for coins from faucet"""
    try:
        _wait_till_open(faucet_url, timeout=120)
        resp = requests.get(f'{faucet_url}/faucet/{currency}?account={account}')
        if resp.status_code == 200:
            return 120.120  # todo: replace with amount
        else:
            raise RuntimeError(f'Failed to get ether from faucet: {resp.status_code}')
    except (requests.exceptions.RequestException, ConnectionError):
        raise


def get_balance(faucet_url, account: str, currency: str) -> float:
    """ Uses faucet service to return current balance

        :raises RuntimeError - Faucet failure
        :raises ConnectionError - Connecting to faucet failed
        :raises ValueError - Unknown currency
    """
    try:
        _wait_till_open(faucet_url, timeout=120)
        # todo: move this to global configuration so we can just use ethereum node instead
        resp = requests.get(f'{faucet_url}/faucet/balance/{currency}?account={account}', timeout=120)
        if resp.status_code == 200:
            logger.info(f'Current {currency} balance is: {resp.json()}')
            return resp.json()
        else:
            raise RuntimeError(f'Failed to get balance from faucet: {resp.status_code}')
    except (requests.exceptions.RequestException, ConnectionError) as e:
        raise


def wait_for_balance(address, currency: str, min_balance: float, timeout: int, backoff: int, config):
    t_stop = timeout + time.monotonic()
    while time.monotonic() < t_stop:
        if min_balance > float(get_balance(config['FAUCET_URL'], address, currency)):
            logger.info(f'{currency} balance is less than the minimum amount to start the worker, '
                        f'waiting for confirmations...')
            time.sleep(backoff)
        else:
            logger.info(f'{currency} approved successfully!')
            return
    raise RuntimeError('Balance did not go over minimum in required time')


def get_initial_coins(account: str, currency: str, config: dict):

    try:
        _currency = {'ETH': 'ether',
                     'ENG': 'eng'}[currency]
    except KeyError:
        raise ValueError(f'Tried to get coins for invalid token {currency}')

    min_balance = {'ETH': float(config['MINIMUM_ETHER_BALANCE']),
                   'ENG': float(config['MINIMUM_ENG_BALANCE'])}

    if min_balance[currency] > float(get_balance(config['FAUCET_URL'], account, _currency)):
        logger.info(f'{currency} balance is less than the minimum amount to start the worker')
        if config['ENIGMA_ENV'] == 'MAINNET':
            logger.error(f'Minimum amounts to start are {min_balance["ENG"]} ENG and {min_balance["ETH"]} ETH. '
                         f'Please transfer at least those amounts to the address {account}, wait for confirmation, '
                         f'and relaunch the worker')
        logger.info(f'Trying to get more {currency} for account: {account} from faucet')

        request_coins(config['FAUCET_URL'], account, _currency)

        logger.info(f'Successfully got {currency} from faucet')

        wait_for_balance(account, _currency, min_balance[currency], int(config['BALANCE_WAIT_TIME']), 60, config)
