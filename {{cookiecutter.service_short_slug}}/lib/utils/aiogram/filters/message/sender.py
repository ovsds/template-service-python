import dataclasses
import logging
import typing

import aiogram
import aiogram.filters as aiogram_filters
import aiogram.types as aiogram_types

default_logger = logging.getLogger("aiogram.filters")


@dataclasses.dataclass(frozen=True)
class SenderMessageFilter(aiogram_filters.Filter):
    user_ids: typing.Sequence[int]
    bots_allowed: bool = False
    logger: logging.Logger = default_logger

    async def __call__(self, message: aiogram_types.Message, bot: aiogram.Bot) -> bool:
        if not message.from_user:
            self.logger.debug("Message has no sender")
            return False

        if not self.bots_allowed and message.from_user.is_bot:
            self.logger.debug("Message sender is a bot")
            return False

        if message.from_user.id not in self.user_ids:
            self.logger.debug("Message sender is not in the allowed users list")
            return False

        self.logger.debug("Message sender is in the allowed users list")
        return True


__all__ = [
    "SenderMessageFilter",
]
