"""
Websocket clients should not know how to receive data, that's left to the underlying framework used.
They should only know about how to manage the received data, that's why facades package.
This way websocket clients no longer need to be tied to a framework, and
so migrating from one framework to the other should be easier.
I would just need to swap the implementation of IWsFacade and the app would work the same way without further changes.5
"""
import abc


class IWsFacade(abc.ABC):
    @abc.abstractmethod
    def on_message(self, message: str):
        raise NotImplemented()

    @abc.abstractmethod
    def on_connected(self, address: str):
        raise NotImplemented()

    @abc.abstractmethod
    def on_open(self):
        raise NotImplemented()

    @abc.abstractmethod
    def on_closed(self, code, reason):
        raise NotImplemented()
