def remove_0x(hexstr: str) -> str:
    """ Remove leading 0x from a hex string """
    if not isinstance(hexstr, str):
        raise TypeError('Parameter must be a string')
    if hexstr.startswith('0x'):
        return hexstr[2:]
    else:
        return hexstr
