from enigma_docker_common.logger import get_logger


def run():
    logger = get_logger('test')
    logger.info(f'Log level: INFO')
    logger.debug('and this shouldn\'t work')
    logger.setLevel("DEBUG")
    logger.debug('this should work')


if __name__ == '__main__':
    run()