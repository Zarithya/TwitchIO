from __future__ import annotations

from typing import Any, Literal, TypedDict, Union

from typing_extensions import NotRequired

__all__ = (
    "SubscriptionTransport",
    "Subscription",
    "WebsocketMessageMetadata",
    "WebsocketMessage",
    "WebsocketMessagePayload",
    "WebhookMessage",
    "HTTPSubscribeResponse",
)


class SubscriptionTransport(TypedDict):
    method: str
    callback: NotRequired[str]
    session_id: NotRequired[str]


class Subscription(TypedDict):
    id: str
    status: str
    type: str
    version: str
    cost: int
    condition: Condition
    created_at: str
    transport: SubscriptionTransport


class HTTPSubscribeResponse(TypedDict):
    data: list[Subscription]
    total: int
    total_cost: int
    max_total_cost: int


class WebsocketMessageMetadata(TypedDict):
    message_id: str
    message_timestamp: str
    message_type: Literal["notification", "revocation", "reconnect", "session_keepalive"]
    subscription_type: NotRequired[str]
    subscription_version: NotRequired[str]


class WebsocketMessagePayload(TypedDict):
    subscription: Subscription
    event: dict[str, AllPayloads]


class WebsocketReconnectPayload(TypedDict):
    session: WebsocketMessageReconnectPayloadSession


class WebsocketMessageReconnectPayloadSession(TypedDict):
    id: str
    status: Literal["reconnecting"]
    keepalive_timeout_seconds: int | None
    reconnect_url: str
    connected_at: str


class WebsocketMessage(TypedDict):
    metadata: WebsocketMessageMetadata
    payload: NotRequired[WebsocketMessagePayload]


class WebsocketReconnectMessage(TypedDict):
    metadata: WebsocketMessageMetadata
    payload: WebsocketReconnectPayload


class WebhookMessage(TypedDict):
    subscription: Subscription
    payload: dict[str, AllPayloads]


class WebhookChallenge(TypedDict):
    subscription: Subscription
    challenge: str


class Condition(TypedDict):
    broadcaster_user_id: NotRequired[str]
    to_broadcaster_user_id: NotRequired[str]
    from_broadcaster_user_id: NotRequired[str]
    moderator_user_id: NotRequired[str]
    reward_id: NotRequired[str]

    extension_client_id: NotRequired[str]
    client_id: NotRequired[str]

    # these are for drops, which arent implemented
    category_id: NotRequired[str]
    campaign_id: NotRequired[str]


## raw payloads


class Images(TypedDict):
    url_1x: str
    url_2x: str
    url_4x: str


class ChannelUpdate(TypedDict):  # channel.update, version 1, NOAUTH
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    title: str
    language: str
    category_id: str
    category_name: str
    is_mature: bool


class ChannelFollow(TypedDict):  # channel.follow, version 1, NOAUTH
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    followed_at: str


class ChannelSubscribe(TypedDict):  # channel.subscribe, version 1, channel:read:subscriptions
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    tier: str
    is_gift: bool


class ChannelSubscriptionEnd(TypedDict):  # channel.subscription.end, version 1, channel:read:subscriptions
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    is_gift: bool


class ChannelSubscriptionGift(TypedDict):  # channel.subscription.gift, version 1, channel:read:subscriptions
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    total: int
    tier: str
    cumulative_total: str
    is_anonymous: bool


class ChannelSubscriptionMessage_Message_Emote(TypedDict):
    begin: int
    end: int
    id: str


class ChannelSubscriptionMessage_Message(TypedDict):
    text: str
    emotes: list[ChannelSubscriptionMessage_Message_Emote]


class ChannelSubscriptionMessage(TypedDict):  # channel.subscription.message, version 1, channel:read:subscriptions
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    tier: str
    cumulative_months: int
    streak_months: int | None
    duration_months: int
    message: ChannelSubscriptionMessage_Message


class ChannelCheer(TypedDict):  # channel.cheer, version 1, bits:read
    is_anonymous: bool
    user_id: str | None
    user_login: str | None
    user_name: str | None
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    message: str
    bits: int


class ChannelRaid(TypedDict):  # channel.raid, version 1, NOAUTH
    from_broadcaster_user_id: str
    from_broadcaster_user_name: str
    from_broadcaster_user_login: str
    to_broadcaster_user_id: str
    to_broadcaster_user_name: str
    to_broadcaster_user_login: str
    viewers: int


class ChannelBan(TypedDict):  # channel.ban, version 1, channel:moderate
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_name: str
    broadcaster_user_login: str
    moderator_user_id: str
    moderator_user_login: str
    moderator_user_name: str
    reason: str
    banned_at: str
    ends_at: str | None
    is_permanent: bool


class ChannelUnban(TypedDict):  # channel.unban, version 1, channel:moderate
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    moderator_user_id: str
    moderator_user_login: str
    moderator_user_name: str


class ChannelModeratorAdd(TypedDict):  # channel.moderator.add, version 1, moderation:read
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str


class ChannelModeratorRemove(TypedDict):  # channel.moderator.remove, version 1, moderation:read
    user_id: str
    user_login: str
    user_name: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str


class ChannelCustomReward_streamlimits(TypedDict):
    is_enabled: bool
    value: int


class ChannelCustomReward_global_cooldown(TypedDict):
    is_enabled: bool
    seconds: int


class ChannelCustomRewardModify(TypedDict):
    # channel.channel_points_custom_reward.add | channel.channel_points_custom_reward.update | channel.channel_points_custom_reward.remove,
    # version 1, channel:read:redemptions or channel:manage:redemptions
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    is_enabled: bool
    is_paused: bool
    is_in_stock: bool
    title: str
    cost: int
    prompt: str
    is_user_input_required: bool
    should_redemptions_skip_request_queue: bool
    cooldown_expires_at: str | None
    redemptions_redeemed_current_stream: int | None
    background_color: str
    max_per_stream: ChannelCustomReward_streamlimits
    max_per_user_per_stream: ChannelCustomReward_streamlimits
    global_cooldown: ChannelCustomReward_global_cooldown
    image: Images
    default_image: Images


class ChannelCustomRewardRedemptionModify_Reward(TypedDict):
    id: str
    title: str
    cost: int
    prompt: str


class ChannelCustomRewardRedemptionModify(TypedDict):
    # channel.channel_points_custom_reward_redemption.add | channel.channel_points_custom_reward_redemption.update
    # version 1, channel:read:redemptions or channel:manage:redemptions
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    user_id: str
    user_login: str
    user_name: str
    user_input: str
    status: Literal["unfulfilled", "fulfilled", "cancelled"]
    reward: ChannelCustomRewardRedemptionModify_Reward
    redeemed_at: str


class ChannelPollBegin_Choice(TypedDict):
    id: str
    title: str


class ChannelPoll_VotingData(TypedDict):
    is_enabled: bool
    amount_per_vote: int


class ChannelPollBegin(TypedDict):  # channel.poll.begin, version 1, channel:read:polls or channel:manage:polls
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    title: str
    choices: list[ChannelPollBegin_Choice]
    bits_voting: ChannelPoll_VotingData
    channel_points_voting: ChannelPoll_VotingData
    started_at: str
    ends_at: str


class ChannelPollProgress_Choice(TypedDict):
    id: str
    title: str
    bits_votes: int
    channel_points_votes: int
    votes: int


class ChannelPollProgress(TypedDict):  # channel.poll.progress, version 1, channel:read:polls or channel:manage:polls
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    title: str
    choices: list[ChannelPollProgress_Choice]
    bits_voting: ChannelPoll_VotingData
    channel_points_voting: ChannelPoll_VotingData
    started_at: str
    ends_at: str


class ChannelPollEnd(TypedDict):  # channel.poll.end, version 1, channel:read:polls or channel:manage:polls
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    title: str
    choices: list[ChannelPollProgress_Choice]
    bits_voting: ChannelPoll_VotingData
    channel_points_voting: ChannelPoll_VotingData
    started_at: str
    status: str
    ended_at: str


class ChannelPredictionBegin_outcomes(TypedDict):
    id: str
    title: str
    color: str


class ChannelPredictionBegin(TypedDict):
    # channel.prediction.begin, version 1, channel:read:predictions or channel:manage:predictions
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    title: str
    outcomes: list[ChannelPredictionBegin_outcomes]
    started_at: str
    locks_at: str


class ChannelPredictionProgressEnd_outcomes_predictor(TypedDict):
    user_id: str
    user_login: str
    user_name: str
    channel_points_won: int | None
    channel_points_used: int


class ChannelPredictionProgressEnd_outcomes(TypedDict):
    id: str
    title: str
    color: str
    users: int
    channel_points: int
    top_predictors: list[ChannelPredictionProgressEnd_outcomes_predictor]  # max 10 users


class ChannelPredictionProgressLock(TypedDict):
    # channel.prediction.progress | channel.prediction.lock,
    # version 1, channel:read:predictions or channel:manage:predictions
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    title: str
    outcomes: list[ChannelPredictionProgressEnd_outcomes]
    started_at: str
    locks_at: str  # progress
    locked_at: str  # lock


class ChannelPredictionEnd(ChannelPredictionProgressLock):
    # channel.prediction.end, version 1, channel:read:predictions or channel:manage:predictions
    status: Literal["resolved", "canceled"]
    winning_outcome_id: str
    ended_at: str


class ChannelHypeTrain_Contributor(TypedDict):
    user_id: str
    user_login: str
    user_name: str
    type: Literal["bits", "subscription"]
    total: int


class ChannelHypeTrainBeginProgress(TypedDict):
    # channel.hype_train.begin | channel.hype_train.progress,
    # version 1, channel:read:hype_train
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    total: int
    progress: int
    goal: int
    top_contributions: list[ChannelHypeTrain_Contributor]
    last_contribution: ChannelHypeTrain_Contributor
    level: int
    started_at: str
    expires_at: str


class ChannelHypeTrainEnd(TypedDict):  # channel.hype_train.end, version 1, channel:read:hype_train
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    total: int
    top_contributions: list[ChannelHypeTrain_Contributor]
    level: int
    started_at: str
    ended_at: str
    cooldown_ends_at: str


class ExtensionBittransactionCreate_Product(TypedDict):
    name: str
    sku: str
    bits: int
    in_development: bool


class ExtensionBittransactionCreate(TypedDict):
    # extension.bits_transaction.create, version 1, oauth token client id must match extension client id
    id: str
    extension_client_id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    user_id: str
    user_login: str
    user_name: str
    product: ExtensionBittransactionCreate_Product


class _ChannelGoal(TypedDict):
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    type: Literal["subscription"]
    description: str
    current_amount: int
    target_amount: int


class ChannelGoalBeginProgress(_ChannelGoal):
    # channel.goal.begin | channel.goal.progress, version 1, channel:read:goals
    started_at: str


class ChannelGoalEnd(_ChannelGoal):  # channel.goal.end, version 1, channel:read:goals
    is_achieved: bool
    started_at: str
    ended_at: str


class StreamOnline(TypedDict):  # stream.online, version 1, NOAUTH
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    type: Literal["live"]
    started_at: str


class StreamOffline(TypedDict):  # stream.offline, version 1, NOAUTH
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str


class UserAuthorizationGrant(TypedDict):  # user.authorization.grant, version 1, NOAUTH
    client_id: str
    user_id: str
    user_login: str
    user_name: str


class UserAuthorizationRevoke(TypedDict):  # user.authorization.revoke, version 1, NOAUTH
    client_id: str
    user_id: str
    user_login: str | None
    user_name: str | None


class UserUpdate(TypedDict):
    # user.update, version 1, NOAUTH (if have user:read:email, notification will include email field)
    user_id: str
    user_login: str
    user_name: str
    email: str | None
    email_verified: bool
    description: str

class _ChannelShieldmode(TypedDict):
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    moderator_user_id: str
    moderator_user_login: str
    moderator_user_name: str


class ChannelShieldModeBegin(_ChannelShieldmode):
    # channel.shield_mode.begin, version 1, moderator:read:shield_mode or moderator:manage:shield_mode (note that this is for the moderator, not broadcaster)
    started_at: str


class ChannelShieldModeEnd(_ChannelShieldmode):
    # channel.shield_mode.end, version 1, moderator:read:shield_mode or moderator:manage:shield_mode (note that this is for the moderator, not broadcaster)
    ended_at: str

# BETA events


class ChannelCharitycampaignDonate_amount(TypedDict):
    value: int
    decimal_places: int
    currency: str


class ChannelCharitycampaignDonate(TypedDict):  # channel.charity_campaign.donate, version beta, channel:read:charity
    campaign_id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    user_id: str
    user_login: str
    user_name: str
    charity_name: str
    charity_description: str
    charity_logo: str
    charity_website: str
    amount: ChannelCharitycampaignDonate_amount


class ChannelCharitycampaignStart(TypedDict):  # channel.charity_campaign.start, version beta, channel:read:charity
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    charity_name: str
    charity_description: str
    charity_logo: str
    charity_website: str
    current_amount: ChannelCharitycampaignDonate_amount
    target_amount: ChannelCharitycampaignDonate_amount
    started_at: str


class ChannelCharitycampaignProgress(TypedDict):
    # channel.charity_campaign.progress, version beta, channel:read:charity
    # note: its possible to receive this before the Start event
    id: str
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    charity_name: str
    charity_description: str
    charity_logo: str
    charity_website: str
    current_amount: ChannelCharitycampaignDonate_amount
    target_amount: ChannelCharitycampaignDonate_amount


class ChannelCharitycampaignStop(ChannelCharitycampaignProgress):
    # channel.charity_campaign.stop, version beta, channel:read:charity
    stopped_at: str


class ChannelGuestStarSessionBegin(TypedDict):
    # channel.guest_star_session.begin, version beta, channel:read:guest_star or channel:manage:guest_star
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    session_id: str
    started_at: str


class ChannelGuestStarSessionEnd(TypedDict):
    # channel.guest_star_session.end, version beta, channel:read:guest_star or channel:manage:guest_star
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    session_id: str
    started_at: str
    ended_at: str


class ChannelGuestStarGuestUpdate(TypedDict):
    # channel.guest_star_guest.update, version beta, 
    # channel:read:guest_star or channel:manage:guest_star or moderator:read:guest_star or moderator:manage:guest_star
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    session_id: str
    moderator_user_id: str
    moderator_user_login: str
    moderator_user_name: str
    guest_user_id: str
    guest_user_name: str
    guest_user_login: str
    slot_id: str
    state: Literal["live", "removed", "backstage", "ready", "invited"]


class ChannelGuestStarGuestSlotUpdate(TypedDict):
    # channel.guest_star_slot.update, version beta, 
    # channel:read:guest_star or channel:manage:guest_star or moderator:read:guest_star or moderator:manage:guest_star
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    session_id: str
    moderator_user_id: str
    moderator_user_login: str
    moderator_user_name: str
    guest_user_id: str
    guest_user_name: str
    guest_user_login: str
    slot_id: str
    host_video_enabled: bool
    host_audio_enabled: bool
    host_volume: int


class ChannelGuestStarSettingsUpdate(TypedDict):
    # channel.guest_star_settings.update, version beta, 
    # channel:read:guest_star or channel:manage:guest_star or moderator:read:guest_star or moderator:manage:guest_star
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    slot_count: int
    is_moderator_send_live_enabled: bool
    is_browser_source_audio_enabled: bool
    group_layout: Literal["tiled", "screenshare"]


AllPayloads = Union[
    ChannelUpdate,
    ChannelFollow,
    ChannelSubscribe,
    ChannelSubscriptionEnd,
    ChannelSubscriptionGift,
    ChannelSubscriptionMessage,
    ChannelCheer,
    ChannelRaid,
    ChannelBan,
    ChannelUnban,
    ChannelModeratorAdd,
    ChannelModeratorRemove,
    ChannelCustomRewardModify,
    ChannelCustomRewardRedemptionModify,
    ChannelPollBegin,
    ChannelPollProgress,
    ChannelPollEnd,
    ChannelPredictionBegin,
    ChannelPredictionEnd,
    ChannelHypeTrainBeginProgress,
    ChannelHypeTrainEnd,
    ChannelGoalBeginProgress,
    ChannelGoalEnd,
    StreamOnline,
    StreamOffline,
    UserAuthorizationGrant,
    UserAuthorizationRevoke,
    UserUpdate,
    # BETA
    ChannelCharitycampaignDonate,
    ChannelCharitycampaignStart,
    ChannelCharitycampaignProgress,
    ChannelCharitycampaignStop,
    ChannelShieldModeBegin,
    ChannelShieldModeEnd,
]
