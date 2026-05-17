from abc import ABC, abstractmethod


class Client(ABC):
    registry = {}
    @abstractmethod
    def start(self):
        pass

    @classmethod
    def register(cls, name: str):
        def decorator(factory_class):
            cls.registry[name] = factory_class
            return factory_class
        return decorator
    
    @classmethod
    def get_factory(cls, name: str):
        return cls.registry.get(name)
