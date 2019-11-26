import socket
import os

from typing import AnyStr, Any
from pathlib import Path

from urllib.parse import urlparse
from azure.storage.blob import BlobClient
import requests


class AzureContainerFileService:
    def __init__(self, directory: str):
        self.account_name = 'objectstorage2'
        self.account_url = f'https://{self.account_name}.blob.core.windows.net/'
        self.container_name = directory
        self.credential = os.getenv('STORAGE_CONNECTION_STRING')

    def __getitem__(self, item: str):
        blob = BlobClient(account_url=self.account_url, container_name=self.container_name, blob_name=item,
                          credential=self.credential)

        blob_data = b''
        for data in blob.download_blob():
            blob_data += data
        return blob_data

    def __setitem__(self, key: str, value: Any):
        if not self.credential:
            raise PermissionError('Credentials in environment variable "STORAGE_CONNECTION_STRING" not set')
        raise NotImplementedError


class HttpFileService:
    def __init__(self, url, namespace: str = 'contract'):
        p = urlparse(url)
        self.hostname = p.hostname
        self.port = p.port
        self.account_url = f'{url}/{namespace}/address?name='
        self.credential = os.getenv('STORAGE_CONNECTION_STRING')

    def __getitem__(self, item):
        addr = requests.get(f'{self.account_url}{item}')
        return addr.json()

    def __setitem__(self, key: str, value: Any):
        if not self.credential:
            raise PermissionError('Credentials in environment variable "STORAGE_CONNECTION_STRING" not set')
        raise NotImplementedError

    def is_ready(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((self.hostname, self.port))
        return result == 0


class LocalStorage:
    def __init__(self, directory: str, flags: str = 'b+'):
        self.path = Path(directory)
        os.makedirs(self.path, exist_ok=True)
        self.flags = flags

    def __getitem__(self, item: str):
        with open(self.path / item, 'r'+self.flags) as f:
            return f.read()

    def __setitem__(self, key: str, value: AnyStr):
        with open(self.path / key, 'w'+self.flags) as f:
            f.write(value)
