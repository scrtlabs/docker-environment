import typing


def remove_0x(hexstr: str) -> str:
    """ Remove leading 0x from a hex string """
    if not isinstance(hexstr, str):
        raise TypeError('Parameter must be a string')
    if hexstr.startswith('0x'):
        return hexstr[2:]
    return hexstr


def parse_env_file(file: typing.Iterable[typing.Text]) -> dict:
    """Parse a .env file to a dict"""
    # noinspection PyTypeChecker
    return dict(
        # we ignore the types because mypy doesn't realize dict can take a Generator[List] where len(list) == 2.
        line.rstrip().split('=', 1)  # type: ignore
        for line
        in file
        if not line.startswith('#')
    )


def dump_env_file(env_vars: dict, file: typing.TextIO) -> None:
    file.writelines(f'{key}={value}\n' for key, value in env_vars.items() if value not in ['', None])
