import asyncio
from quart import websocket  # Import Quart's websocket context

class WebSocketHelper:
    clients = set()
    # Class variable to store connected clients

    @classmethod
    async def register(cls):
        cls.clients.add(websocket._get_current_object())
        # Class method to register a websocket client

    @classmethod
    async def unregister(cls):
        cls.clients.remove(websocket._get_current_object())
        # Class method to unregister a websocket client

    @classmethod
    async def broadcast(cls, message):
        if cls.clients:
            await asyncio.gather(*(client.send(message) for client in cls.clients))
            # Use asyncio.gather to concurrently send messages to all clients
        # Class method to broadcast a message to all connected clients
