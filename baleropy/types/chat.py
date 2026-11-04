from __future__ import annotations

from enum import Enum

from .base import BoundObject


class ChatType(str, Enum):
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"
    SUPERGROUP = "supergroup"


class ChatAction(str, Enum):
    TYPING = "typing"
    UPLOAD_PHOTO = "upload_photo"
    RECORD_VIDEO = "record_video"
    UPLOAD_VIDEO = "upload_video"
    RECORD_VOICE = "record_voice"
    UPLOAD_VOICE = "upload_voice"
    CHOOSE_STICKER = "choose_sticker"


class User(BoundObject):
    id: int
    is_bot: bool = False
    first_name: str = ""
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() if self.last_name else self.first_name

    @property
    def mention(self) -> str:
        return f"@{self.username}" if self.username else self.full_name


class ChatPhoto(BoundObject):
    small_file_id: str
    small_file_unique_id: str
    big_file_id: str
    big_file_unique_id: str


class Chat(BoundObject):
    id: int
    type: ChatType | str
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class ChatFullInfo(Chat):
    photo: ChatPhoto | None = None
    bio: str | None = None
    description: str | None = None
    invite_link: str | None = None
    linked_chat_id: str | None = None


class ChatMemberStatus(str, Enum):
    CREATOR = "creator"
    ADMINISTRATOR = "administrator"
    MEMBER = "member"
    RESTRICTED = "restricted"
    LEFT = "left"
    KICKED = "kicked"


class ChatMember(BoundObject):
    """Union of the Bale ChatMember* objects, discriminated by ``status``."""

    status: ChatMemberStatus | str
    user: User
    is_member: bool | None = None
    can_delete_messages: bool | None = None
    can_manage_video_chats: bool | None = None
    can_restrict_members: bool | None = None
    can_promote_members: bool | None = None
    can_change_info: bool | None = None
    can_invite_users: bool | None = None
    can_post_stories: bool | None = None
    can_post_messages: bool | None = None
    can_edit_messages: bool | None = None
    can_pin_messages: bool | None = None
    can_send_messages: bool | None = None
    can_send_audios: bool | None = None
    can_send_documents: bool | None = None
    can_send_photos: bool | None = None
    can_send_videos: bool | None = None

    @property
    def is_admin(self) -> bool:
        return self.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)

    @property
    def is_joined(self) -> bool:
        if self.status == ChatMemberStatus.RESTRICTED:
            return bool(self.is_member)
        return self.status not in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)


class WebhookInfo(BoundObject):
    url: str = ""


class ResponseParameters(BoundObject):
    retry_after: int | None = None


__all__ = [
    "Chat",
    "ChatAction",
    "ChatFullInfo",
    "ChatMember",
    "ChatMemberStatus",
    "ChatPhoto",
    "ChatType",
    "ResponseParameters",
    "User",
    "WebhookInfo",
]
