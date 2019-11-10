import time

import requests

from .logger import get_logger

logger = get_logger('eng_common.faucet')


def request_coins(faucet_url, account: str, currency: str) -> bool:
    """ Issue a requests for coins from faucet"""
    if currency not in ['ETH', 'ENG']:
        raise ValueError(f'Requested balance for invalid currency {currency}')

    # faucet currency convert to match the faucet service. todo: change in faucet
    _cur = {'ETH': 'ether',
            'ENG': 'eng'}

    try:
        resp = requests.get(f'{faucet_url}/faucet/{_cur}?account={account}', timeout=120)
        if resp.status_code == 200:
            return True
        else:
            logger.error(f'Failed to get ether from faucet: {resp.status_code}')
    except requests.exceptions.RequestException:
        return False


def get_balance(faucet_url, account: str, currency: str) -> float:
    """ Uses faucet service to return current balance

        :raises RuntimeError - Faucet failure
        :raises ConnectionError - Connecting to faucet failed
        :raises ValueError - Unknown currency
    """
    if currency not in ['ether', 'eng']:
        raise ValueError(f'Requested balance for invalid currency {currency}')
    logger.info(f'Trying to get {currency} balance account: {account}')
    try:
        # todo: move this to global configuration so we can just use ethereum node instead
        resp = requests.get(f'{faucet_url}/faucet/balance/{currency}?account={account}', timeout=120)
        if resp.status_code == 200:
            logger.info(f'Current {currency} balance is: {resp.json()}')
            return resp.json()
        else:
            raise RuntimeError(f'Failed to get balance from faucet: {resp.status_code}')
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f'Failed to connect to faucet: {e}')


def wait_for_balance(address, currency: str, min_balance: float, timeout: int, backoff: int, config):
    t_stop = timeout + time.monotonic()
    while time.monotonic() < t_stop:
        if min_balance > float(get_balance(config['FAUCET_URL'], address, currency)):
            logger.info(f'{currency} balance is less than the minimum amount to start the worker, '
                        f'waiting for confirmations...')
            time.sleep(backoff)
        else:
            logger.info(f'{currency} approved successfully!')
            return True
    return False


def get_initial_coins(account: str, currency: str, config: dict):
    if currency not in ['ETH', 'ENG']:
        logger.critical(f'Tried to get coins for invalid token {currency}')
        exit(-3)

    min_balance = {'ETH': float(config['MINIMUM_ETHER_BALANCE']),
                   'ENG': float(config['MINIMUM_ENG_BALANCE'])}

    if min_balance[currency] > float(get_balance(config['FAUCET_URL'], account, currency)):
        logger.info(f'{currency} balance is less than the minimum amount to start the worker')
        if config['ENIGMA_ENV'] == 'MAINNET':
            logger.error(f'Minimum amounts to start are {min_balance["ENG"]} ENG and {min_balance["ETH"]} ETH. '
                         f'Please transfer at least those amounts to the address {account}, wait for confirmation, '
                         f'and relaunch the worker')
        logger.info(f'Trying to get more {currency} for account: {account} from faucet')
        if not request_coins(config['FAUCET_URL'], account, 'ether'):
            logger.critical(f'Exiting...')
            return False

        logger.info(f'Successfully got {currency} from faucet')

        if not wait_for_balance(account, currency, min_balance[currency], int(config['BALANCE_WAIT_TIME']), 60, config):
            logger.error(f'Not enough {currency} to run the worker, exiting...')
            return False
    return True