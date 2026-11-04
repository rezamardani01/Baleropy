from __future__ import annotations

from typing import Any, ClassVar

from ..types import ChatFullInfo, ChatMember
from ..types.input_file import InputFile
from .base import BaleMethod

ChatId = int | str


class _ChatBool(BaleMethod[bool]):
    __returning__: ClassVar = bool
    chat_id: ChatId


class BanChatMember(_ChatBool):
    __api_method__: ClassVar[str] = "banChatMember"
    user_id: int


class UnbanChatMember(_ChatBool):
    __api_method__: ClassVar[str] = "unbanChatMember"
    user_id: int
    only_if_banned: bool | None = None


class PromoteChatMember(_ChatBool):
    __api_method__: ClassVar[str] = "promoteChatMember"
    user_id: int
    can_change_info: bool | None = None
    can_post_messages: bool | None = None
    can_edit_messages: bool | None = None
    can_delete_messages: bool | None = None
    can_manage_video_chats: bool | None = None
    can_invite_users: bool | None = None
    can_restrict_members: bool | None = None


class SetChatPhoto(_ChatBool):
    __api_method__: ClassVar[str] = "setChatPhoto"
    photo: InputFile


class DeleteChatPhoto(_ChatBool):
    __api_method__: ClassVar[str] = "deleteChatPhoto"


class LeaveChat(_ChatBool):
    __api_method__: ClassVar[str] = "leaveChat"


class GetChat(BaleMethod[ChatFullInfo]):
    __api_method__: ClassVar[str] = "getChat"
    __returning__: ClassVar = ChatFullInfo
    chat_id: ChatId


class GetChatAdministrators(BaleMethod[list[ChatMember]]):
    __api_method__: ClassVar[str] = "getChatAdministrators"
    __returning__: ClassVar = list[ChatMember]
    chat_id: ChatId


class GetChatMembersCount(BaleMethod[int]):
    __api_method__: ClassVar[str] = "getChatMembersCount"
    __returning__: ClassVar = int
    chat_id: ChatId


class GetChatMember(BaleMethod[ChatMember]):
    __api_method__: ClassVar[str] = "getChatMember"
    __returning__: ClassVar = ChatMember
    chat_id: ChatId
    user_id: int


class PinChatMessage(_ChatBool):
    __api_method__: ClassVar[str] = "pinChatMessage"
    message_id: int


class UnpinChatMessage(_ChatBool):
    __api_method__: ClassVar[str] = "unpinChatMessage"
    message_id: int


class UnpinAllChatMessages(_ChatBool):
    __api_method__: ClassVar[str] = "unpinAllChatMessages"


class SetChatTitle(_ChatBool):
    __api_method__: ClassVar[str] = "setChatTitle"
    title: str


class SetChatDescription(_ChatBool):
    __api_method__: ClassVar[str] = "setChatDescription"
    description: str


class CreateChatInviteLink(BaleMethod[Any]):
    __api_method__: ClassVar[str] = "createChatInviteLink"
    __returning__: ClassVar = Any
    chat_id: ChatId


class RevokeChatInviteLink(BaleMethod[Any]):
    __api_method__: ClassVar[str] = "revokeChatInviteLink"
    __returning__: ClassVar = Any
    chat_id: ChatId
    invite_link: str


class ExportChatInviteLink(BaleMethod[str]):
    __api_method__: ClassVar[str] = "exportChatInviteLink"
    __returning__: ClassVar = str
    chat_id: ChatId
