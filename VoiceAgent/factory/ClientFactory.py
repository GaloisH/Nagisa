from clients.client import Client
import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)


class ClientFactory:
    def create_client(self, name: str, *args, **kwargs):
        client = Client.get_factory(name)
        if client is None:
            raise ValueError(f"Client '{name}' is not registered.")
        return client(*args, **kwargs)
