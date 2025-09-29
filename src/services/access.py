from aiogram.types import CallbackQuery, TelegramObject
from aiogram_dialog.utils import remove_intent_id
from loguru import logger

from src.core.constants import PURCHASE_PREFIX
from src.core.enums import AccessMode
from src.core.storage.keys import AccessModeKey, AccessWaitListKey
from src.core.utils.formatters import format_log_user
from src.infrastructure.database.models.dto import UserDto
from src.infrastructure.taskiq.tasks.notifications import (
    send_access_denied_notifications_task,
    send_access_opened_notifications_task,
)

from .base import BaseService


class AccessService(BaseService):
    async def is_access_allowed(self, user: UserDto, event: TelegramObject) -> bool:
        if user.is_blocked:
            logger.info(f"{format_log_user(user)} Access denied (user blocked)")
            return False

        mode = await self.get_current_mode()

        if mode == AccessMode.ALL:
            return True

        if user.is_privileged:
            logger.debug(f"{format_log_user(user)} Access allowed (privileged user)")
            return True

        match mode:
            case AccessMode.BLOCKED:
                logger.info(f"{format_log_user(user)} Access denied (mode: blocked)")

                await send_access_denied_notifications_task.kiq(
                    user=user,
                    i18n_key="ntf-access-denied",
                )

                return False

            case AccessMode.PURCHASE:
                if self._is_purchase_action(event):
                    logger.info(f"{format_log_user(user)} Access denied (mode: no purchases)")

                    await send_access_denied_notifications_task.kiq(
                        user=user,
                        i18n_key="ntf-access-denied-purchase",
                    )

                    if await self._can_add_to_waitlist(user.telegram_id):
                        await self.add_user_to_waitlist(user.telegram_id)

                    return False
                return True

            case AccessMode.INVITED:
                if await self.is_invited(user):
                    logger.debug(f"{format_log_user(user)} Access allowed (mode: invited)")
                    return True

                logger.debug(f"{format_log_user(user)} Access denied (not invited)")
                return False

            case _:
                logger.warning(f"{format_log_user(user)} Unknown access mode '{mode}'")
                return False

    async def is_invited(self, user: UserDto) -> bool:
        # TODO: Replace with actual referral check
        return True

    async def get_current_mode(self) -> AccessMode:
        return await self.redis_repository.get(  # type: ignore[return-value]
            key=AccessModeKey(),
            validator=AccessMode,
            default=AccessMode.ALL,
        )

    async def get_available_modes(self) -> list[AccessMode]:
        current = await self.get_current_mode()
        return [mode for mode in AccessMode if mode != current]

    async def set_mode(self, mode: AccessMode) -> None:
        await self.redis_repository.set(key=AccessModeKey(), value=mode)
        logger.debug(f"Access mode changed to '{mode}'")

        if mode in (AccessMode.ALL, AccessMode.INVITED):
            waiting_users = await self.get_all_waiting_users()
            if waiting_users:
                logger.info(f"Notifying {len(waiting_users)} waiting users about access opening")
                await send_access_opened_notifications_task.kiq(waiting_users)

        await self.clear_all_waiting_users()

    async def add_user_to_waitlist(self, telegram_id: int) -> bool:
        added_count = await self.redis_repository.collection_add(AccessWaitListKey(), telegram_id)

        if added_count > 0:
            logger.info(f"User '{telegram_id}' added to access waitlist")
            return True

        logger.debug(f"User '{telegram_id}' already in access waitlist")
        return False

    async def remove_user_from_waitlist(self, telegram_id: int) -> bool:
        removed_count = await self.redis_repository.collection_remove(
            AccessWaitListKey(),
            telegram_id,
        )

        if removed_count > 0:
            logger.info(f"User '{telegram_id}' removed from access waitlist")
            return True

        logger.debug(f"User '{telegram_id}' not found in access waitlist")
        return False

    async def get_all_waiting_users(self) -> list[int]:
        members_str = await self.redis_repository.collection_members(key=AccessWaitListKey())
        users = [int(member) for member in members_str]
        logger.debug(f"Retrieved '{len(users)}' users from access waitlist")
        return users

    async def clear_all_waiting_users(self) -> None:
        await self.redis_repository.delete(key=AccessWaitListKey())
        logger.info("Access waitlist completely cleared")

    async def _can_add_to_waitlist(self, telegram_id: int) -> bool:
        is_member = await self.redis_repository.collection_is_member(
            key=AccessWaitListKey(),
            value=telegram_id,
        )
        if is_member:
            logger.debug(f"User '{telegram_id}' already in access waitlist")
            return False

        logger.debug(f"User '{telegram_id}' can be added to access waitlist")
        return True

    def _is_purchase_action(self, event: TelegramObject) -> bool:
        if not isinstance(event, CallbackQuery) or not event.data:
            return False

        callback_data = remove_intent_id(event.data)

        if callback_data[-1].startswith(PURCHASE_PREFIX):
            logger.debug(f"Detected purchase action: {callback_data}")
            return True

        return False
