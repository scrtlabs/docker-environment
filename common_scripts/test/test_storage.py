import pytest

from common_scripts.enigma_docker_common.storage import LocalStorage

@pytest.fixture(scope='module')
def localstorage():
    fs = LocalStorage(directory='/home/bob/newfolder')
    yield fs


def test_read_write_file(localstorage):
    expected = "hello"
    localstorage["file"] = expected
    content = localstorage["file"]

    assert content == expected
