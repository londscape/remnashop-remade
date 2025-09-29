from uuid import UUID

from aiogram import Bot
from fluentogram import TranslatorHub
from redis.asyncio import Redis
from remnawave import RemnawaveSDK
from remnawave.models import CreateUserRequestDto, UpdateUserRequestDto, UserResponseDto

from src.core.config import AppConfig
from src.core.enums import SubscriptionStatus
from src.core.utils.formatters import (
    format_days_to_datetime,
    format_device_count,
    format_gb_to_bytes,
)
from src.infrastructure.database.models.dto import PlanSnapshotDto, UserDto
from src.infrastructure.redis import RedisRepository

from .base import BaseService


class RemnawaveService(BaseService):
    def __init__(
        self,
        config: AppConfig,
        bot: Bot,
        redis_client: Redis,
        redis_repository: RedisRepository,
        translator_hub: TranslatorHub,
        #
        remnawave: RemnawaveSDK,
    ) -> None:
        super().__init__(config, bot, redis_client, redis_repository, translator_hub)
        self.remnawave = remnawave

    async def create_user(self, user: UserDto, plan: PlanSnapshotDto) -> UserResponseDto:
        created_user = await self.remnawave.users.create_user(
            CreateUserRequestDto(
                expire_at=format_days_to_datetime(plan.duration),
                username=user.remna_name,
                traffic_limit_bytes=format_gb_to_bytes(plan.traffic_limit),
                # traffic_limit_strategy=,
                description=user.remna_description,
                # tag=,
                telegram_id=user.telegram_id,
                hwidDeviceLimit=format_device_count(plan.device_limit),
                active_internal_squads=[str(uid) for uid in plan.squad_ids],
            )
        )

        if not isinstance(created_user, UserResponseDto):
            raise ValueError

        return created_user

    async def updated_user(
        self,
        user: UserDto,
        plan: PlanSnapshotDto,
        uuid: UUID,
    ) -> UserResponseDto:
        created_user = await self.remnawave.users.update_user(
            UpdateUserRequestDto(
                uuid=uuid,
                active_internal_squads=[str(uid) for uid in plan.squad_ids],
                description=user.remna_description,
                expire_at=format_days_to_datetime(plan.duration),
                hwidDeviceLimit=format_device_count(plan.device_limit),
                status=SubscriptionStatus.ACTIVE,
                # tag=,
                telegram_id=user.telegram_id,
                traffic_limit_bytes=format_gb_to_bytes(plan.traffic_limit),
                # traffic_limit_strategy=,
            )
        )

        if not isinstance(created_user, UserResponseDto):
            raise ValueError

        return created_user
