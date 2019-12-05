import os
import time
import pathlib
import subprocess
import argparse

SGX_ENV_PATH = '/opt/sgxsdk/environment'

from enigma_docker_common.config import Config
from enigma_docker_common.logger import get_logger

logger = get_logger('worker.core-startup')

required = ['RUST_BACKTRACE', 'SPID', 'PORT', 'ATTESTATION_RETRIES']

env_defaults = {'K8S': './core/config/k8s_config.json',
                'TESTNET': './core/config/testnet_config.json',
                'MAINNET': './core/config/mainnet_config.json',
                'COMPOSE': './core/config/compose_config.json'}


def init_arg_parse() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("-e", "--executable", help="Path to Key Management executable", type=str,
                        default='/root/core/bin/enigma-core-app')
    return p


def map_log_level_to_exec_flags(loglevel: str) -> str:
    level = loglevel.upper()
    if level == "DEBUG":
        return '-vvv'
    if level == "INFO":
        return '-vv'
    if level == "WARNING":
        return '-v'
    else:
        return ''


def main():
    parser = init_arg_parse()
    args = parser.parse_args()

    try:
        config = Config(config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])
    except (ValueError, IOError):
        exit(-1)

    if not os.getenv('RUST_BACKTRACE'):
        if config['RUST_BACKTRACE'] != '0':
            os.environ["RUST_BACKTRACE"] = config['RUST_BACKTRACE']

    debug_trace_flags = map_log_level_to_exec_flags(config.get('LOG_LEVEL', 'INFO'))
    spid = config['SPID']
    port = config['PORT']
    attestation_retries = config['ATTESTATION_RETRIES']
    os.chdir(pathlib.Path(args.executable).parent)

    # wait for SGX service to start
    time.sleep(2)
    env = os.environ.copy()
    logger.debug(f'Environment: {env}')
    subprocess.call([f'{args.executable}', f'{debug_trace_flags}',
                     '-p', f'{port}',
                     '--spid', f'{spid}',
                     '-r', f'{attestation_retries}'], env=env)


if __name__ == '__main__':
    main()
