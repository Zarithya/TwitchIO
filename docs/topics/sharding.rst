:orphan:

.. currentmodule:: twitchio

.. _sharding:

Sharding
=========
If you've used previous versions of TwitchIO,
you may have gotten to a point where the library was no longer able to keep up to the amount of data coming in.
You'd have noticed that TwitchIO did not have the capability to split its connections to handle more data, and 
could't handle more than ~100 channels per Client.
TwitchIO 3 changes all that, with built in sharding support.
Sharding is entirely transparent to everyday usage of the library, and can be implemented once you need it, without any code refactoring.
All that needs to be changed is passing a Shard Manager to your :class:`Client` / :class:`~twitchio.ext.commands.Bot`, via the ``shard_manager=`` parameter.

.. note::

    When passing a Shard Manager to your :class:`Client` / :class:`~twitchio.ext.commands.Bot`, take care to pass the `type` and not an `instance`.
    TwitchIO will create the instance internally, once it is ready.
    If you pass an instance, TwitchIO will ignore it and create a new one instead.

    This is correct:

    .. code-block:: python

        import twitchio

        client = twitchio.Client(
            twitchio.SimpleTokenHandler(...),
            shard_manager=twitchio.DistributedShardManager
        )
    
    This is wrong:

    .. code-block:: python

        import twitchio

        client = twitchio.Client(
            twitchio.SimpleTokenHandler(...),
            shard_manager=twitchio.DistributedShardManager()
        )

Setting one up
---------------
If you're already familiar with :ref:`token handlers <tokens>`, you'll find Shard Managers quite similar in design.
However, shard managers are significantly more low-level, and will need a bit more skill, as the library will not handle errors from within gracefully.
If you don't feel up to the task, but still would like to take advantage of sharding, the library has a couple built in Shard Managers that might suit you.

Default Shard Manager
+++++++++++++++++++++++
Firstly, the :class:`Default Shard Manager <DefaultShardManager>` is what the library uses any time you don't specify a Shard Manager.
This Shard Manager uses exactly one connection, and everything goes through that one shard.
Functionality-wise, this is identical to previous versions of TwitchIO.

Distributed Shard Manager
++++++++++++++++++++++++++
Another approach is to use the :class:`Distributed Shard Manager <DistributedShardManager>`, which opens multiple shards under the same user.
It will then balance all channels to be joined across the shards, creating new ones as needed.
When you pass the :class:`DistributedShardManager` to :class:`Client`, you'll also have the ability to pass arguments to it via the :class:`Client` constructor.

For example, to limit the amount of channels per shard to 10, we can pass ``channels_per_shard`` to :class:`Client`, like so:

.. code-block:: python

    import twitchio

    client = twitchio.Client(
        twitchio.SimpleTokenHandler(...),
        shard_manager=twitchio.DistributedShardManager,
        channels_per_shard=10
    )

This will pass ``channels_per_shard`` to the :class:`DistributedShardManager`, ensuring that each shard has at maximum 10 channels.

All arguments that the :class:`DistributedShardManager` takes are documented :class:`here <DistributedShardManager>`.

More shard managers to come
++++++++++++++++++++++++++++
...


Building your own
------------------
The power of Shard Managers lies in being able to build one yourself, so let's take a look at doing that.
To do so, we're going to make use of an existing Shard Manager; the :class:`Distributed Shard Manager <DistributedShardManager>`.

A Shard Manager subclasses needs the following methods:

- :meth:`~BaseShardManager.assign_shard`
- :meth:`~BaseShardManager.start`
- :meth:`~BaseShardManager.stop`
- :meth:`~BaseShardManager.get_sender_shard`

Additionally, we can use :meth:`~BaseShardManager.setup` to set up our shards in an async environment.

The :class:`Default Shard Manager <DefaultShardManager>` looks like this:

.. code-block:: python

    class DefaultShardManager(twitchio.BaseShardManager):
        main_shard: Shard

        async def setup(self, **kwargs) -> None:
            _, user = await self.token_handler._client_get_irc_login(self.client, None)
            self.main_shard = self.add_shard("main-shard", user.name)
        
        async def assign_shard(self, channel_name: str, is_initial_channel: bool) -> None:
            if is_initial_channel:
                return
            
            await self.main_shard.add_channels((channel_name,))
        
        async def start(self) -> None:
            await self.main_shard.start(block=True)
        
        async def stop(self) -> None:
            await self.main_shard.stop()
        
        async def get_sender_shard(self, channel_name: str) -> Shard:
            return self.main_shard

This minimal Shard Manager creates one shard, and uses it for everything.
It fetches an IRC token by calling ``_client_get_irc_login``, which is an internal method for calling 
:meth:`TokenHandler.get_irc_token(None) <BaseTokenHandler.get_irc_token>`.

That example works fine, but what if we want to add more shards? Maybe we want to balance users across shards.
We can do that using the :class:`DistributedShardManager`, which is a tad bit more complex than the :class:`DefaultShardManager`.

.. code-block:: python
    
    class DistributedShardManager(BaseShardManager):
        authorized_name: str
        next_shard_id: int

        async def setup(self, **kwargs) -> None:
            self.next_shard_id = 1
            self.channels_per_shard: int = kwargs.get("channels_per_shard", 25)
            self.max_shard_count: int = kwargs.get("max_shard_count", 5)
            initial_shards: int = kwargs.get("initial_shard_count", 1)

            _, user = await self.token_handler._client_get_irc_login(self.client, None) # type: ignore
            self.authorized_name = user.name

            if self.initial_channels:
                assignable = list(self.initial_channels)
                slice_size = math.floor(len(assignable) / initial_shards)

                if slice_size > self.channels_per_shard: # we need to add more shards to startup
                    initial_shards = math.ceil(len(assignable) / self.channels_per_shard)
                    if initial_shards > self.max_shard_count:
                        raise RuntimeError("More channels have been added to initial_channels than are allowed by the combination "
                                        "of channels_per_shard and max_shard_count. Consider using larger amounts for these values.")

                    slice_size = math.floor(len(assignable) / initial_shards)

                for idx in range(1, initial_shards+1):
                    if idx < initial_shards:
                        chnl_slice = assignable[:slice_size]
                        assignable = assignable[slice_size:]
                    else:
                        chnl_slice = assignable
                    
                    self.add_shard(f"initial-shard-{idx}", self.authorized_name, initial_channels=chnl_slice)
            else:
                for idx in range(initial_shards):
                    self.add_shard(f"initial-shard-{idx}", self.authorized_name)

        async def assign_shard(self, channel_name: str, is_initial_channel: bool) -> None:
            if is_initial_channel:
                return
            
            ideal_shard = min(self.shards.values(), key=lambda shard: len(shard.websocket._channels))

            if len(ideal_shard.websocket._channels) >= self.channels_per_shard:
                if len(self.shards) >= self.max_shard_count:
                    raise RuntimeError("All shards are full, and the shard count limit has been reached.")

                new_shard_id = f"extended-shard-{self.next_shard_id}"
                self.next_shard_id += 1

                ideal_shard = self.add_shard(new_shard_id, self.authorized_name)
                await ideal_shard.start(block=False)
            
            await ideal_shard.add_channels((channel_name,))
        
        async def start(self) -> None:
            await self.start_all_shards()
            await self.wait_until_exit()
        
        async def stop(self) -> None:
            await self.stop_all_shards()
            
        async def get_sender_shard(self, channel_name: str) -> Shard:
            return next(iter(self.shards.values()))

Woah, that's quite a lot. Let's break it down, step by step:

.. code-block:: python

    class DistributedShardManager(BaseShardManager):
        authorized_name: str
        next_shard_id: int

        async def setup(self, **kwargs) -> None:
            self.next_shard_id = 1 # this is used to give shards added later a unique name.

            # fetch our arguments from the Client args, with some sane defaults.
            self.channels_per_shard: int = kwargs.get("channels_per_shard", 25)
            self.max_shard_count: int = kwargs.get("max_shard_count", 5)
            initial_shards: int = kwargs.get("initial_shard_count", 1)

            # Same as the DefaultShardManager, we grab the token to use by calling token_handler.get_irc_token(None)
            _, user = await self.token_handler._client_get_irc_login(self.client, None)
            self.authorized_name = user.name # all we care about is the username.

            if self.initial_channels:
                assignable = list(self.initial_channels)
                slice_size = math.floor(len(assignable) / initial_shards) # how many channels per shard.

                if slice_size > self.channels_per_shard: # we need to add more shards to startup, because all of the initial shards are full.
                    initial_shards = math.ceil(len(assignable) / self.channels_per_shard)
                    if initial_shards > self.max_shard_count:
                        raise RuntimeError("More channels have been added to initial_channels than are allowed by the combination "
                                        "of channels_per_shard and max_shard_count. Consider using larger amounts for these values.")

                    slice_size = math.floor(len(assignable) / initial_shards) # re-assess how many channels per shard.

                for idx in range(1, initial_shards+1):
                    if idx < initial_shards:
                        chnl_slice = assignable[:slice_size] # grab the first N channels.
                        assignable = assignable[slice_size:] # remove those channels from the assignable list.
                    else:
                        chnl_slice = assignable # last socket, assign all remaining channels.
                    
                    self.add_shard(f"initial-shard-{idx}", self.authorized_name, initial_channels=chnl_slice)
            else:
                for idx in range(1, initial_shards+1): # no initial channels, simple logic!
                    self.add_shard(f"initial-shard-{idx}", self.authorized_name)

This is the business end of the Shard Manager. It takes our arguments from the :class:`Client` constructor, and uses them to 
spread out channels across our shards. If needed, it'll make more shards than originally requested.

For the rest of this example, we'll remove the body of the ``prepare`` function to keep things clean.

After creating the initial shards, we need a way to add channels later. That's where :meth:`~BaseShardManager.assign_shard` comes in.
Let's take a look:

.. code-block:: python

    class DistributedShardManager(BaseShardManager):
        authorized_name: str
        next_shard_id: int

    async def setup(self, **kwargs) -> None:
        ... # SNIP

    async def assign_shard(self, channel_name: str, is_initial_channel: bool) -> None:
        if is_initial_channel: 
            # We've already assigned all the initial channels in the setup() function, so we won't worry about them here.
            # An important note, this function will be called for every single initial channel, so be sure to ignore them if you've already assigned them,
            # like we have in this example.
            return
        
        # find the shard with the least amount of channels.
        ideal_shard = min(self.shards.values(), key=lambda shard: len(shard.websocket._channels))

        # if the least amount of channels is still our max amount per shard, create a new shard.
        if len(ideal_shard.websocket._channels) >= self.channels_per_shard:
            if len(self.shards) >= self.max_shard_count:
                # we've hit the configured max shard count!
                raise RuntimeError("All shards are full, and the shard count limit has been reached.")
            
            # get a unique shard id, and increment the counter for the next time.
            new_shard_id = f"extended-shard-{self.next_shard_id}"
            self.next_shard_id += 1

            # create the new shard, and start it immediatly.
            ideal_shard = self.add_shard(new_shard_id, self.authorized_name)
            await ideal_shard.start(block=False)
        
        # add our channel to the ideal shard.
        await ideal_shard.add_channels((channel_name,))

After startup, this is the only other time you'll need to handle balancing users.
The library will do the heavy lifting after this point.

However, there are a few more things the library needs you to do.
You'll need to determine how the shards start and stop, and what shard should send messages to certain channels.
Let's take a look:

.. code-block:: python

    class DistributedShardManager(BaseShardManager):
        authorized_name: str
        next_shard_id: int

    async def setup(self, **kwargs) -> None:
        ... # SNIP

    async def assign_shard(self, channel_name: str, is_initial_channel: bool) -> None:
        ... # SNIP
    
    async def start(self) -> None:
        # these are both built in helper functions. You should almost never need anything more than these.
        await self.start_all_shards()
        await self.wait_until_exit()
    
    async def stop(self) -> None:
        # this is also a helper function. It'll do the trick just fine.
        await self.stop_all_shards()
        
    async def get_sender_shard(self, channel_name: str) -> Shard:
        # this part is a little trickier.
        # we need to get a shard to send messages from for the specified channel name.
        # that channel_name is the target channel, so if you've got different users logged in on different shards
        # (for example, custom bot names would have a dedicated shard for that bot user).

        # however, since the DistributedShardManager uses the same user for all its shards,
        # we can use the first shard that comes up. The shard does not have to have joined the channel to send a message there.
        return next(iter(self.shards.values()))

And that's all there is to it. You can make your Shard Manager as small or as complex as you need,
all by overriding these functions.