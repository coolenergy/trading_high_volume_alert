from abc import ABC

from autobahn.asyncio.websocket import WebSocketClientProtocol

from ws_facades import IWsFacade


class AbstractAutobahnWsClient(IWsFacade, WebSocketClientProtocol, ABC):

    def onConnect(self, response):
        self.on_connected(str(response.peer))

    def onOpen(self):
        self.on_open()

    def onMessage(self, payload, isBinary):
        if isBinary:
            print(f"Binary message received: {len(payload)} bytes")
        else:
            self.on_message(payload)

    # noinspection PyPep8Naming
    def onClose(self, wasClean, code, reason):
        self.on_closed(code, reason)

    def __call__(self, *args, **kwargs):
        return self
