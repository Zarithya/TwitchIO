.. currentmodule:: twitchio.ext.eventsub

.. _eventsub_ref:

Eventsub ext
=============

This ext is split into multiple sections to make navigation easier.
If you're looking for the API reference, :ref:`click here <eventsub_api_ref>`.
If you're new to the ext, continue reading!


.. _eventsub_subclass_ref:

Getting started
----------------

Eventsub is the way to receive most live events from twitch. If you've used previous versions of Twitchio's eventsub implementation,
you've probably been scarred by how janky and broken they've been. Some of you have also had to deal with the hassle of needing the events client-side,
which wasn't really possible with the old implementations. If you haven't had to use the old versions, congratulations, you've avoided an awful experience!
The new eventsub module has been rewritten from scratch to make life as easy as possible for you the developer.
It is completely independant of the core library's :class:`~twitchio.Client`, meaning you can simply plug a :ref:`token handler <tokens>` into the eventsub client,
and be on your way. Speaking of standalone eventsub clients, the new way to create these revolves around subclassing. Let's take a look:

.. code:: python

    import twitchio
    from twitchio.ext import eventsub

    class MyEventsubClient(eventsub.Client):
        async def event_channel_update(self, event: eventsub.NotificationEvent[eventsub.ChannelUpdate]) -> None:
            print(f"Channel {event.data.broadcaster.name} has updated their channel! The title is: {event.data.title}")
    
    ...

Business and logic now belong inside of the subclass, and you can do whatever you want from within.
To subscribe to events, you'll need to create an instance of the eventsub client, and pass it a token handler.
The token handler is explained in much greater detail :ref:`here <tokens>`, but for now we'll just use the :class:`~twitchio.SimpleTokenHandler` to use one token for everything.

.. code:: python

    import twitchio
    from twitchio.ext import eventsub

    class MyEventsubClient(eventsub.Client):
        async def event_channel_update(self, event: eventsub.NotificationEvent[eventsub.ChannelUpdate]) -> None:
            print(f"Channel {event.data.broadcaster.name} has updated their channel! The title is: {event.data.title}")
    
    async def main():
        token_handler = twitchio.SimpleTokenHandler("token", "client-id")
        ...

Now that we have an instance of the token handler, we'll also need a :ref:`transport <eventsub_transport>`. We'll go into greater detail about trasports later,
for now we'll simply say that transports are what tell the library how to send and receive data from twitch. Currently twitch provides two transports,
``webhooks`` and ``websockets``. This example will use the ``websocket`` transport so that you can run it on your own computer without needing a webserver.
Setting up the websocket transport is as easy as creating an instance of it:

.. code:: python

    import asyncio
    import twitchio
    from twitchio.ext import eventsub

    class MyEventsubClient(eventsub.Client):
        async def event_channel_update(self, event: eventsub.NotificationEvent[eventsub.ChannelUpdate]) -> None:
            print(f"Channel {event.data.broadcaster.name} has updated their channel! The title is: {event.data.title}")
    
    async def main():
        token_handler = twitchio.SimpleTokenHandler("token", "client-id")
        transport = eventsub.WebsocketTransport()
        ...
    
    asyncio.run(main())

Now that we have everything we need to create our eventsub client, we can do so by passing the two things to the instance:

.. code:: python

    import asyncio
    import twitchio
    from twitchio.ext import eventsub

    class MyEventsubClient(eventsub.Client):
        async def event_channel_update(self, event: eventsub.NotificationEvent[eventsub.ChannelUpdate]) -> None:
            print(f"Channel {event.data.broadcaster.name} has updated their channel! The title is: {event.data.title}")
    
    async def main():
        token_handler = twitchio.SimpleTokenHandler("token", "client-id")
        transport = eventsub.WebsocketTransport()
        eventsub_client = MyEventsubClient(transport, token_handler)
        ...
    
    asyncio.run(main())

With our eventsub client set up, we can create subscriptions to the topics. When using the ``websocket`` transport, we need to have tokens with the correct
scopes, otherwise we won't have permission to create the subscriptions
(note that when using the ``webhook`` transport, twitch validates the tokens server-side, so you won't need the tokens directly).
So, assuming that the token has the correct scopes (You can check which scopes your token will need with the 
`Twitch Dev docs <https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/>`_), we can create the subscription:

.. code:: python

    import asyncio
    import twitchio
    from twitchio.ext import eventsub

    class MyEventsubClient(eventsub.Client):
        async def event_channel_update(self, event: eventsub.NotificationEvent[eventsub.ChannelUpdate]) -> None:
            print(f"Channel {event.data.broadcaster.name} has updated their channel! The title is: {event.data.title}")
    
    async def main():
        token_handler = twitchio.SimpleTokenHandler("token", "client-id")
        transport = eventsub.WebsocketTransport()
        eventsub_client = MyEventsubClient(transport, token_handler)
        await eventsub_client.subscribe_channel_update(user)
        ...
    
    asyncio.run(main())

But wait, that code won't work. We need to tell the library who to subscribe to, and for that we need a :class:`~twitchio.PartialUser` object. 
Unfortunately, to get a :class:`~twitchio.PartialUser`, we'd need a :class:`twitchio.Client`, which the ext works without. So instead, we can use a
:class:`~twitchio.DummyUser`, which is an object we can make ourselves, and isn't attached to a Client from the core library. 
We'll need to know the ID of user beforehand, and you can get that by either calling :meth:`twitchio.Client.fetch_users` to convert the username to the ID,
or you can use one of the many online tools to do so. For this example, I'll use a fake ID, however to successfully make a subscription you'll need to find your own.

.. code:: python

    import asyncio
    import twitchio
    from twitchio.ext import eventsub

    class MyEventsubClient(eventsub.Client):
        async def event_channel_update(self, event: eventsub.NotificationEvent[eventsub.ChannelUpdate]) -> None:
            print(f"Channel {event.data.broadcaster.name} has updated their channel! The title is: {event.data.title}")
    
    async def main():
        token_handler = twitchio.SimpleTokenHandler("token", "client-id")
        transport = eventsub.WebsocketTransport()
        eventsub_client = MyEventsubClient(transport, token_handler)
        user = twitchio.DummyUser(id=123456789)
        await eventsub_client.subscribe_channel_update(user)
        ...
    
    asyncio.run(main())

Alright, we've successfully made a subscription to for user 123456789 on channel updates. However there's one problem that you might've noticed.
The program exits immediatly, and we don't get to see any events come through. This happens because we don't have any other code that runs after the subscription is created,
so the program runs to the end of the main function and then exits. We can fix this by adding a while true loop that has an await in it:

.. code:: python

    import asyncio
    import twitchio
    from twitchio.ext import eventsub

    class MyEventsubClient(eventsub.Client):
        async def event_channel_update(self, event: eventsub.NotificationEvent[eventsub.ChannelUpdate]) -> None:
            print(f"Channel {event.data.broadcaster.name} has updated their channel! The title is: {event.data.title}")
    
    async def main():
        token_handler = twitchio.SimpleTokenHandler("token", "client-id")
        transport = eventsub.WebsocketTransport()
        eventsub_client = MyEventsubClient(transport, token_handler)
        user = twitchio.DummyUser(id=123456789)
        await eventsub_client.subscribe_channel_update(user)
        
        while True:
            await asyncio.sleep(0)
    
    asyncio.run(main())

This code will run forever, listening for channel updates.

That's all for the intro/tutorial to standalone eventsub. For a more technical dive into things, keep reading below.

.. _eventsub_transport:
