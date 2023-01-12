
import twitchio
from twitchio.ext import eventsub
import asyncio

import logging
logging.basicConfig()

async def main():
    transport = eventsub.WebhookTransport("a", "https://example.com/a")
    ec = eventsub.Client(transport)
    await ec.start()
    
    return
    tokens = twitchio.SimpleTokenHandler("snt9otojezvz9q7fknfer49mwddxpz", "gp762nuuoqcoxypju8c569th9wz7q5", "qdojgwrnb6f59doblnmdspe16fhahzqkmhxa46gtsin7r7w1kq")

    async with twitchio.Client(tokens, initial_channels=["iamtomahawkx"]) as client:
        data = await client.fetch_user("iamtomahawkx")
        print(data)
        print(await data.fetch_active_extensions()) # broken

asyncio.run(main())