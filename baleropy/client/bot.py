from __future__ import annotations

import asyncio
import io
import re
from pathlib import Path
from typing import Any, BinaryIO, TypeVar

from .. import methods as m
from ..methods.base import BaleMethod
from ..methods.media_group import AnyInputMedia
from ..methods.misc import InputSticker
from ..types import (
    ChatAction,
    ChatFullInfo,
    ChatMember,
    File,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    MessageId,
    ReplyMarkup,
    StickerSet,
    Transaction,
    Update,
    User,
    WebhookInfo,
)
from ..types.input_file import InputFile
from ..types.markup import ButtonRows, _build_inline_markup, _build_reply_markup
from .server import BUSINESS, PRODUCTION, ApiServer
from .session.aiohttp import AiohttpSession
from .session.base import BaseSession

T = TypeVar("T")
ChatId = int | str
FileInput = InputFile | str

_TOKEN_RE = re.compile(r"^\d+:[\w-]+$")


def validate_token(token: str) -> str:
    if not isinstance(token, str) or not _TOKEN_RE.match(token.strip()):
        raise ValueError("Token has an invalid format, expected '<digits>:<secret>'")
    return token.strip()


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class Bot:
    """Entry point to the Bale Bot API.

    Use shortcuts (``await bot.send_message(...)``) or method objects
    (``await bot(SendMessage(...))``).
    """

    def __init__(
        self,
        token: str,
        session: BaseSession | None = None,
        server: ApiServer = PRODUCTION,
    ) -> None:
        self.token = validate_token(token)
        self.session = session or AiohttpSession()
        self.server = server
        self._me: User | None = None

    @classmethod
    def business(cls, token: str, session: BaseSession | None = None) -> Bot:
        """A bot for the Business API (bulk messaging with a separate, paid rate quota).

        Only getMe, sendMessage, forwardMessage, sendPhoto, sendVideo, sendAudio and sendDocument
        are available; ``chat_id`` must be a private chat and files can only be sent by ``file_id``.
        """
        return cls(token, session, server=BUSINESS)

    @property
    def id(self) -> int:
        return int(self.token.split(":", 1)[0])

    async def __call__(self, method: BaleMethod[T]) -> T:
        return await self.session(self, method)

    async def __aenter__(self) -> Bot:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self.session.close()

    async def me(self) -> User:
        """Cached result of ``getMe``."""
        if self._me is None:
            self._me = await self.get_me()
        return self._me

    # --- updates ---------------------------------------------------------------------------
    async def get_updates(
        self, offset: int | None = None, limit: int | None = None, timeout: int | None = None
    ) -> list[Update]:
        return await self(m.GetUpdates(offset=offset, limit=limit, timeout=timeout))

    async def set_webhook(self, url: str) -> bool:
        return await self(m.SetWebhook(url=url))

    async def delete_webhook(self) -> bool:
        return await self(m.DeleteWebhook())

    async def get_webhook_info(self) -> WebhookInfo:
        return await self(m.GetWebhookInfo())

    # --- bot -------------------------------------------------------------------------------
    async def get_me(self) -> User:
        return await self(m.GetMe())

    async def ask_review(self, user_id: int, delay_seconds: int) -> bool:
        return await self(m.AskReview(user_id=user_id, delay_seconds=delay_seconds))

    # --- sending ---------------------------------------------------------------------------
    async def send_message(
        self,
        chat_id: ChatId,
        text: str,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
        *,
        buttons: ButtonRows | None = None,
    ) -> Message:
        if buttons is not None:
            if reply_markup is not None:
                raise ValueError("Use either buttons or reply_markup, not both")
            reply_markup = _build_reply_markup(buttons)
        return await self(
            m.SendMessage(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def forward_message(
        self, chat_id: ChatId, from_chat_id: ChatId, message_id: int
    ) -> Message:
        return await self(
            m.ForwardMessage(chat_id=chat_id, from_chat_id=from_chat_id, message_id=message_id)
        )

    async def copy_message(
        self, chat_id: ChatId, from_chat_id: ChatId, message_id: int
    ) -> MessageId:
        return await self(
            m.CopyMessage(chat_id=chat_id, from_chat_id=from_chat_id, message_id=message_id)
        )

    async def send_photo(
        self,
        chat_id: ChatId,
        photo: FileInput,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        return await self(
            m.SendPhoto(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def send_audio(
        self,
        chat_id: ChatId,
        audio: FileInput,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        return await self(
            m.SendAudio(
                chat_id=chat_id,
                audio=audio,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def send_document(
        self,
        chat_id: ChatId,
        document: FileInput,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        return await self(
            m.SendDocument(
                chat_id=chat_id,
                document=document,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def send_video(
        self,
        chat_id: ChatId,
        video: FileInput,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        return await self(
            m.SendVideo(
                chat_id=chat_id,
                video=video,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def send_animation(
        self,
        chat_id: ChatId,
        animation: FileInput,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        return await self(
            m.SendAnimation(
                chat_id=chat_id,
                animation=animation,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def send_voice(
        self,
        chat_id: ChatId,
        voice: FileInput,
        caption: str | None = None,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        return await self(
            m.SendVoice(
                chat_id=chat_id,
                voice=voice,
                caption=caption,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def send_sticker(
        self,
        chat_id: ChatId,
        sticker: FileInput,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        return await self(
            m.SendSticker(
                chat_id=chat_id,
                sticker=sticker,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def send_media_group(
        self,
        chat_id: ChatId,
        media: list[AnyInputMedia],
        reply_to_message_id: int | None = None,
    ) -> list[Message]:
        return await self(
            m.SendMediaGroup(chat_id=chat_id, media=media, reply_to_message_id=reply_to_message_id)
        )

    async def send_location(
        self,
        chat_id: ChatId,
        latitude: float,
        longitude: float,
        horizontal_accuracy: float | None = None,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        return await self(
            m.SendLocation(
                chat_id=chat_id,
                latitude=latitude,
                longitude=longitude,
                horizontal_accuracy=horizontal_accuracy,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def send_contact(
        self,
        chat_id: ChatId,
        phone_number: str | int,
        first_name: str,
        last_name: str | None = None,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        return await self(
            m.SendContact(
                chat_id=chat_id,
                phone_number=phone_number,
                first_name=first_name,
                last_name=last_name,
                reply_to_message_id=reply_to_message_id,
                reply_markup=reply_markup,
            )
        )

    async def send_chat_action(self, chat_id: ChatId, action: ChatAction | str) -> bool:
        return await self(m.SendChatAction(chat_id=chat_id, action=action))

    # --- editing ---------------------------------------------------------------------------
    async def edit_message_text(
        self,
        chat_id: ChatId,
        message_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        *,
        buttons: ButtonRows | None = None,
    ) -> Message | bool:
        if buttons is not None:
            if reply_markup is not None:
                raise ValueError("Use either buttons or reply_markup, not both")
            reply_markup = _build_inline_markup(buttons)
        return await self(
            m.EditMessageText(
                chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup
            )
        )

    async def edit_message_caption(
        self,
        chat_id: ChatId,
        message_id: int,
        caption: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
        *,
        buttons: ButtonRows | None = None,
    ) -> Message | bool:
        if buttons is not None:
            if reply_markup is not None:
                raise ValueError("Use either buttons or reply_markup, not both")
            reply_markup = _build_inline_markup(buttons)
        return await self(
            m.EditMessageCaption(
                chat_id=chat_id, message_id=message_id, caption=caption, reply_markup=reply_markup
            )
        )

    async def edit_message_reply_markup(
        self,
        chat_id: ChatId,
        message_id: int,
        reply_markup: InlineKeyboardMarkup | None = None,
        *,
        buttons: ButtonRows | None = None,
    ) -> Message | bool:
        if buttons is not None:
            if reply_markup is not None:
                raise ValueError("Use either buttons or reply_markup, not both")
            reply_markup = _build_inline_markup(buttons)
        return await self(
            m.EditMessageReplyMarkup(
                chat_id=chat_id, message_id=message_id, reply_markup=reply_markup
            )
        )

    async def delete_message(self, chat_id: ChatId, message_id: int) -> bool:
        return await self(m.DeleteMessage(chat_id=chat_id, message_id=message_id))

    async def answer_callback_query(
        self, callback_query_id: str, text: str | None = None, show_alert: bool | None = None
    ) -> bool:
        return await self(
            m.AnswerCallbackQuery(
                callback_query_id=callback_query_id, text=text, show_alert=show_alert
            )
        )

    # --- chats -----------------------------------------------------------------------------
    async def get_chat(self, chat_id: ChatId) -> ChatFullInfo:
        return await self(m.GetChat(chat_id=chat_id))

    async def get_chat_administrators(self, chat_id: ChatId) -> list[ChatMember]:
        return await self(m.GetChatAdministrators(chat_id=chat_id))

    async def get_chat_members_count(self, chat_id: ChatId) -> int:
        return await self(m.GetChatMembersCount(chat_id=chat_id))

    async def get_chat_member(self, chat_id: ChatId, user_id: int) -> ChatMember:
        return await self(m.GetChatMember(chat_id=chat_id, user_id=user_id))

    async def ban_chat_member(self, chat_id: ChatId, user_id: int) -> bool:
        return await self(m.BanChatMember(chat_id=chat_id, user_id=user_id))

    async def unban_chat_member(
        self, chat_id: ChatId, user_id: int, only_if_banned: bool | None = None
    ) -> bool:
        return await self(
            m.UnbanChatMember(chat_id=chat_id, user_id=user_id, only_if_banned=only_if_banned)
        )

    async def promote_chat_member(
        self,
        chat_id: ChatId,
        user_id: int,
        *,
        can_change_info: bool | None = None,
        can_post_messages: bool | None = None,
        can_edit_messages: bool | None = None,
        can_delete_messages: bool | None = None,
        can_manage_video_chats: bool | None = None,
        can_invite_users: bool | None = None,
        can_restrict_members: bool | None = None,
    ) -> bool:
        return await self(
            m.PromoteChatMember(
                chat_id=chat_id,
                user_id=user_id,
                can_change_info=can_change_info,
                can_post_messages=can_post_messages,
                can_edit_messages=can_edit_messages,
                can_delete_messages=can_delete_messages,
                can_manage_video_chats=can_manage_video_chats,
                can_invite_users=can_invite_users,
                can_restrict_members=can_restrict_members,
            )
        )

    async def leave_chat(self, chat_id: ChatId) -> bool:
        return await self(m.LeaveChat(chat_id=chat_id))

    async def set_chat_photo(self, chat_id: ChatId, photo: InputFile) -> bool:
        return await self(m.SetChatPhoto(chat_id=chat_id, photo=photo))

    async def delete_chat_photo(self, chat_id: ChatId) -> bool:
        return await self(m.DeleteChatPhoto(chat_id=chat_id))

    async def set_chat_title(self, chat_id: ChatId, title: str) -> bool:
        return await self(m.SetChatTitle(chat_id=chat_id, title=title))

    async def set_chat_description(self, chat_id: ChatId, description: str) -> bool:
        return await self(m.SetChatDescription(chat_id=chat_id, description=description))

    async def pin_chat_message(self, chat_id: ChatId, message_id: int) -> bool:
        return await self(m.PinChatMessage(chat_id=chat_id, message_id=message_id))

    async def unpin_chat_message(self, chat_id: ChatId, message_id: int) -> bool:
        return await self(m.UnpinChatMessage(chat_id=chat_id, message_id=message_id))

    async def unpin_all_chat_messages(self, chat_id: ChatId) -> bool:
        return await self(m.UnpinAllChatMessages(chat_id=chat_id))

    async def create_chat_invite_link(self, chat_id: ChatId) -> Any:
        return await self(m.CreateChatInviteLink(chat_id=chat_id))

    async def revoke_chat_invite_link(self, chat_id: ChatId, invite_link: str) -> Any:
        return await self(m.RevokeChatInviteLink(chat_id=chat_id, invite_link=invite_link))

    async def export_chat_invite_link(self, chat_id: ChatId) -> str:
        return await self(m.ExportChatInviteLink(chat_id=chat_id))

    # --- files -----------------------------------------------------------------------------
    async def get_file(self, file_id: str) -> File:
        return await self(m.GetFile(file_id=file_id))

    async def download(
        self,
        file: str | File,
        destination: BinaryIO | str | Path | None = None,
        chunk_size: int = 65536,
    ) -> BinaryIO | None:
        """Download a file by ``file_id`` or :class:`File`.

        Returns an in-memory buffer when ``destination`` is omitted, otherwise ``None``.
        """
        if isinstance(file, File) and file.file_path:
            info = file
        else:
            info = await self.get_file(file.file_id if isinstance(file, File) else file)
        if not info.file_path:
            raise ValueError("Bale did not return file_path for this file")
        url = self.server.file_url(self.token, info.file_path)
        buffer = io.BytesIO()
        async for chunk in self.session.stream_content(url, chunk_size):
            buffer.write(chunk)
        if destination is None:
            buffer.seek(0)
            return buffer
        if isinstance(destination, (str, Path)):
            await asyncio.to_thread(_write_file, Path(destination), buffer.getvalue())
        else:
            destination.write(buffer.getvalue())  # noqa: ASYNC240
        return None

    # --- stickers --------------------------------------------------------------------------
    async def upload_sticker_file(self, user_id: int, sticker: InputFile) -> File:
        return await self(m.UploadStickerFile(user_id=user_id, sticker=sticker))

    async def create_new_sticker_set(
        self, user_id: int, name: str, title: str, stickers: list[InputSticker]
    ) -> bool:
        return await self(
            m.CreateNewStickerSet(user_id=user_id, name=name, title=title, stickers=stickers)
        )

    async def add_sticker_to_set(self, user_id: int, name: str, sticker: InputSticker) -> bool:
        return await self(m.AddStickerToSet(user_id=user_id, name=name, sticker=sticker))

    async def get_sticker_set(self, name: str) -> StickerSet:
        return await self(m.GetStickerSet(name=name))

    # --- payments --------------------------------------------------------------------------
    async def send_invoice(
        self,
        chat_id: ChatId,
        title: str,
        description: str,
        payload: str,
        provider_token: str,
        prices: list[LabeledPrice],
        photo_url: str | None = None,
        reply_to_message_id: int | None = None,
    ) -> Message:
        return await self(
            m.SendInvoice(
                chat_id=chat_id,
                title=title,
                description=description,
                payload=payload,
                provider_token=provider_token,
                prices=prices,
                photo_url=photo_url,
                reply_to_message_id=reply_to_message_id,
            )
        )

    async def create_invoice_link(
        self,
        title: str,
        description: str,
        payload: str,
        provider_token: str,
        prices: list[LabeledPrice],
    ) -> str:
        return await self(
            m.CreateInvoiceLink(
                title=title,
                description=description,
                payload=payload,
                provider_token=provider_token,
                prices=prices,
            )
        )

    async def answer_pre_checkout_query(
        self, pre_checkout_query_id: str, ok: bool, error_message: str | None = None
    ) -> bool:
        return await self(
            m.AnswerPreCheckoutQuery(
                pre_checkout_query_id=pre_checkout_query_id, ok=ok, error_message=error_message
            )
        )

    async def inquire_transaction(self, transaction_id: str) -> Transaction:
        return await self(m.InquireTransaction(transaction_id=transaction_id))
