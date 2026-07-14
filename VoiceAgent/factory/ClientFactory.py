from clients.client import Client
import os

class ClientFactory:
    def create_client(self, name: str, *args, **kwargs):
        client = Client.get_factory(name)
        if client is None:
            raise ValueError(f"Client '{name}' is not registered.")
        return client(*args, **kwargs)
