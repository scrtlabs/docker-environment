import json
import os
from collections import UserDict
from .logger import get_logger

logger = get_logger('pycommon.config')

DEFAULT_CONF_PATH = "/conf/"

global_config_paths = {"DEV": "dev_config.json",
                       "COMPOSE": "compose_config.json",
                       "SYSTEST": "systest_config.json",
                       "TESTNET": "testnet_config.json",
                       "TESTNET_DEBUG": '',
                       "MAINNET": "mainnet_config.json"}


env_defaults = {'K8S': './config/k8s_config.json',
                'TESTNET': './config/testnet_config.json',
                'MAINNET': './config/mainnet_config.json',
                'COMPOSE': './config/compose_config.json'}


__all__ = ['Config']


class Config(UserDict):
    """ Configuration manager -- loads global parameters
     automatically selects environment variables first, local configuration second, and global configuration if all else fails

     Can pass a list of required arguments which are checked before initialization passes -- this way you can catch any
     missing parameters early
     """
    def __init__(self, required: list = None, config_file: str = None):
        # don't use mutable objects as default arguments
        self.required = [] if required is None else required

        super().__init__()
        if not config_file:
            config_file = env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')]
        logger.info(f'Loading custom configuration: {config_file}')
        try:
            with open(config_file) as f:
                conf_file = json.load(f)
                self.update(conf_file)
        except IOError:
            logger.critical("there was a problem opening the config file")
            raise
        except json.JSONDecodeError as e:
            logger.critical("config file isn't valid json")
            raise ValueError from e

        self.check_required()

    def check_required(self):
        for key in self.required:
            if key not in self:
                raise EnvironmentError(f'Missing key {key} in configuration file or environment variables')

    def __contains__(self, key):
        if key in os.environ:
            return True
        return super().__contains__(key)

    def __getitem__(self, item):
        """ first search environment variable, and only then our stored keys
         Will search both the key name, and the upper case key name just in case """
        if isinstance(item, str):
            if item in os.environ:
                return os.getenv(item)
            env_name = item.upper()
            if env_name in os.environ:
                return os.getenv(env_name)

        return super().__getitem__(item)
