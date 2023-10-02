.. currentmodule:: twitchio

Event Reference
================

Introduction
-------------
This page contains all events that the library will dispatch, including :ref:`ext.commands <commands_ref>` and :ref:`ext.eventsub <eventsub_ref>`.
This page is a reference guide, and contains up-to-date information on all events the library can dispatch that are intended for public use.

How do I make an event listener
++++++++++++++++++++++++++++++++
events can be created using the :meth:`@client.listen <Client.listen>` decorator, to which you can provide an event name, or you can name your function using the event name.
You can check the :meth:`examples <Client.listen>` for more information.

Alternatively, if using the :ref:`commands ext <commands_ref>`, you can use :meth:`@commands.listen <twitchio.ext.commands.listen>` decorator inside a :class:`~twitchio.ext.commands.Cog` to create an event listener.

Can I make my own events?
++++++++++++++++++++++++++
Sure! To make your own events, first make a listener using the steps above.
Your event will have to take exactly **one** argument (you can make it ``None`` if you don't need an argument).

Next, call :meth:`Client.dispatch_listeners` with your event name (remove the ``event_`` prefix when dispatching), and the argument.
All of your listeners will run with the provided argument.


Core library events
--------------------

.. function:: event_ready(_)

    This event is called when all shards have connected to twitch, and all of them have received the READY event.

    .. versionchanged:: 3.0
        This now takes a dummy argument to comply with the new event dispatcher.
        While it may get used in the future, for now you can ignore it.

    .. warning::
        This function can be called many times, as it is called every time a shard reconnects.
        Do not use it for logic at startup. Instead, use :meth:`Client.setup`.
    
    Parameters
    -----------
    nothing: ``None``
        Literally nothing.

.. function:: event_shard_ready(shard_name: str)
    
    This event is called whenever a shard receives the READY event from twitch.

    .. versionadded:: 3.0

    Parameters
    -----------
    shard_name: :class:`str`
        The name of the shard that has received the READY event.
        Typically this will be the name of the user this shard is logged in as.

.. function:: event_message(message: Message)

    This event is called whenever a chatter sends a message to a channel.

    .. versionchanged:: 3.0
        Removed ECHO messages.
    
    Parameters
    -----------
    message: :class:`Message`
        The message sent to the channel.


.. function:: event_join(chatter: PartialChatter)

    This event is called any time twitch sends a JOIN message.
    This indicates that a chatter has joined a channel 
    (the specific channel can be accessed through :meth:`chatter.channel <PartialChatter.channel>`).

    .. note::
        Typically these are sent in batches every few minutes.
        They are not very precise in timing.

    .. versionchanged:: 3.0
        Removed the ``channel`` argument.
    
    Parameters
    -----------
    chatter: :class:`PartialChatter`
        The chatter that joined.
    
.. function:: event_part(chatter: PartialChatter)

    This event is called any time twitch sends a PART message.
    This indicates that a chatter has left a channel 
    (the specific channel can be accessed through :meth:`chatter.channel <PartialChatter.channel>`).

    .. note::
        Typically these are sent in batches every few minutes.
        They are not very precise in timing.
    
    .. versionchanged:: 3.0
        Removed the ``channel`` argument.
    
    Parameters
    -----------
    chatter: :class:`PartialChatter`
        The chatter that left.


Eventsub events
-----------------
TODO

Commands events
----------------
TODO

pubsub events
--------------
TODO
