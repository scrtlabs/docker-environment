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

    spid = config['SPID']
    port = config['PORT']
    attestation_retries = config['ATTESTATION_RETRIES']
    os.chdir(pathlib.Path(args.executable).parent)

    # wait for SGX service to start
    time.sleep(2)
    env = os.environ.copy()
    logger.debug(f'Environment: {env}')

    exec_args = ['gdbserver',
                 'localhost:7777',
                 f'{args.executable}',
                 '-p', f'{port}',
                 '--spid', f'{spid}',
                 '-r', f'{attestation_retries}']

    log_level = config.get('LOG_LEVEL', '').lower()
    if log_level:
        exec_args.append('-l')
        exec_args.append(log_level)

    subprocess.call(exec_args, env=env)


if __name__ == '__main__':
    main()
