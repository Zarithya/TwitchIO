.. currentmodule:: twitchio

.. _migrating:

Migrating from V2
===================
This page lays out the changes you'll need to make in your code to convert from TwitchIO V2 to V3.


.. _migrating_partialuser:

Changes with PartialUser
--------------------------
The following changes have been made to :class:`PartialUser`.
These changes also apply to :class:`User`, :class:`SearchUser`, and :class:`UserBan`

- :class:`PartialUser` now inherits from :class:`BaseUser`

Additions
++++++++++
The following have been added:

- :meth:`PartialUser.fetch_subscribed_to` (And its model, :class:`SubscribedEvent`)

Removals
+++++++++
The following functions have been removed due to their corresponding API routes being removed:

- :meth:`PartialUser.follow`
- :meth:`PartialUser.unfollow`
- :meth:`PartialUser.replace_tags`
- :meth:`PartialUser.fetch_follow`


Edits 
++++++
The following functions have had edits made to them:

- :meth:`PartialUser.fetch`
    - Removed the ``token`` parameter.
    - Removed the ``force`` parameter.

- :meth:`PartialUser.edit`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.get_custom_rewards` -> :meth:`PartialUser.fetch_custom_rewards`
    - Renamed the method to follow fetch vs. get naming conventions.
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.fetch_bits_leaderboard`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.start_commercial`
    - Removed the ``token`` parameter.
    - The ``length`` parameter now specifies the allowed lengths through ``Literal`` instead of a vague ``int``.

- :meth:`PartialUser.create_clip`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.fetch_clips`
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.fetch_hypetrain_events`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.fetch_bans`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.fetch_ban_events`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.fetch_moderators`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.fetch_mod_events`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.automod_check`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.fetch_stream_key`
    - Removed the ``token`` parameter.
    - This function now returns the documented string instead of a raw response.

- :meth:`PartialUser.fetch_following`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.fetch_followers`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.fetch_subscriptions` -> :meth:`PartialUser.fetch_subscribers`
    - Renamed to avoid intent conflict with :meth:`PartialUser.fetch_subscribed`.
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.create_marker`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.fetch_markers`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.
    - The return signature has changed to tuple[:class:`PartialUser`, :class:`VideoMarkers`]

- :meth:`PartialUser.fetch_extensions`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.fetch_active_extensions`
    - Removed the ``token`` parameter.
    - Added the ``use_app_token`` parameter, to specify what kind of token to use for the request.

- :meth:`PartialUser.update_extension`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.fetch_videos`
    - Removed the ``language`` parameter, as it was ineffective in this context.
    - All parameters now have Literal typehints instead of :class:`str`.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.end_prediction`
    - Removed the ``token`` parameter.
    - The ``status`` parameter now has Literal typehints instead of :class:`str`
    - Added an assert in the function body to ensure winning_outcode_id is set when status is RESOLVED

- :meth:`PartialUser.get_predictions`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.create_prediction`
    - Removed the ``token`` parameter.
    - This function now takes a list of titles as outcomes, instead of blue and pink.
    - Added an assert in the function body to ensure 2 <= outcomes <= 10
    - Added an assert to the function body to ensure 30 <= prediction_window <= 1800

- :meth:`PartialUser.modify_stream` -> :meth:`PartialUser.modify_channel`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.fetch_schedule`
    - Removed the ``utc_offset`` parameter, as twitch no longer supports it.
    - Removed the ``first`` parameter, it is superceded by the :ref:`aai`.
    - Added the ``use_app_token`` parameter, to specify what kind of token to use for the request.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.fetch_channel_teams`
    - Added ``use_app_token`` parameter, to specify what kind of token to use for the request.

- :meth:`PartialUser.fetch_polls`
    - Removed the ``token`` parameter.
    - This function now returns an :ref:`aai`.

- :meth:`PartialUser.create_poll`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.end_poll`
    - Removed the ``token`` parameter.
    - The ``status`` parameter now takes a Literal instead of :class:`str`

- :meth:`PartialUser.shoutout`
    - Removed the ``token`` parameter.
    - Changed the ``target_id`` parameter to ``target_broadcaster`` of type :class:`BaseUser`
    - Changed the ``moderator`` parameter to type :class:`BaseUser` | ``None``

- :meth:`PartialUser.fetch_goals`
    - Removed the ``token`` parameter.

- :meth:`PartialUser.fetch_chat_settings`
    - Removed the ``token`` parameter.
    - Changed the ``moderator_id`` parameter to ``moderator`` of type :class:`BaseUser`

- :meth:`PartialUser.update_chat_settings`
    - Removed the ``token`` parameter.
    - Changed the ``moderator_id`` parameter to ``moderator`` of type :class:`BaseUser`


Client Changes
---------------
The following changes have been made to :class:`~twitchio.Client` 
(and :class:`ext.commands.Bot <twitchio.ext.commands.Bot>` by extension).

:class:`~twitchio.Client` now takes a required parameter: ``token_handler``. Please see :ref:`token handlers <tokens>` for more information.

Additions
++++++++++

- :meth:`Client.fetch_user`
    Shorthand to :meth:`Client.fetch_users` that returns ``User | None``.

Removals
+++++++++

- :meth:`Client.from_client_credentials` (no longer needed, see :ref:`token handling <tokens>`).
- :meth:`Client.connect` (use :meth:`Client.start` instead).
- :meth:`Client.fetch_channel` (use :meth:`Client.fetch_channels` instead).
- :meth:`Client.fetch_webhook_subscriptions` (webhooks are gone).

Edits
++++++

- :meth:`Client.run`
    - Now uses :func:`asyncio.run` as the underlying runner.

- :meth:`Client.add_event` -> :meth:`Client.add_event_listener`
    - This is now documented for public use.

- :meth:`Client.remove_event` -> :meth:`Client.remove_event_listener`
    - This is now documented for public use.

- :meth:`@Client.event <Client.event>` -> :meth:`@Client.listener <Client.listener>`
    - Renamed function for clarity.
    - The decorator can be used without the event name in it now (see the :meth:`example <Client.listener>`).

- :meth:`Client.fetch_users`
    - This function now returns an :ref:`aai`.
    - This function no longer has a cache.
    - Removed the ``force`` parameter.

- :meth:`Client.create_user` -> :meth:`Client.get_partial_user`
    - Renamed function for clarity.

- :meth:`Client.fetch_channels` -> :meth:`Client.fetch_channel_info`
    - Renamed function for clarity.

- :meth:`Client.fetch_videos`
    - This function now returns an :ref:`aai`.
    - Parameters have been reordered to match typical usage.

- :meth:`Client.fetch_chatter_colors`
    - Removed the ``token`` parameter.
    - Added the ``target`` parameter.

- :meth:`Client.update_chatter_color`
    - Removed the ``token`` parameter.
    - Removed the ``user_id`` parameter.
    - Added the ``target`` parameter (combines the removed parameters).
    - The ``color`` parameter now specifies Literals that can be used, along with more specific docstrings.

- :meth:`Client.fetch_games`
    - This function now returns an :ref:`aai`.
    - Added the ``target`` parameter.

- :meth:`Client.fetch_streams`
    - This function now returns an :ref:`aai`.
    - Removed the ``token`` parameter.
    - Added the ``target`` parameter.

- :meth:`Client.fetch_top_games`
    - This function now returns an :ref:`aai`.
    - Added the ``target`` parameter.

- :meth:`Client.fetch_tags`
    - This function now returns an :ref:`aai`.
    - Added the ``target`` parameter.

- :meth:`Client.fetch_team`
    - Added the ``target`` parameter.

- :meth:`Client.delete_videos`
    - Removed the ``token`` parameter.
    - Added the ``target`` parameter.

- :meth:`Client.fetch_global_chat_badges`
    - Added the ``target`` parameter.