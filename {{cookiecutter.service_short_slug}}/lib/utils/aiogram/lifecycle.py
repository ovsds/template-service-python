import asyncio
import dataclasses
import logging

import aiogram

import lib.utils.lifecycle as lifecycle_utils


@dataclasses.dataclass(frozen=True)
class Lifecycle:

    @dataclasses.dataclass(frozen=True)
    class Webhook:
        url: str
        secret_token: str

    logger: logging.Logger
    bot: aiogram.Bot
    dispatcher: aiogram.Dispatcher

    name: str
    description: str
    short_description: str
    commands: list[aiogram.types.BotCommand]
    webhook: Webhook | None = None

    async def setup_telegram_bot_name(self) -> None:
        name = await self.bot.get_my_name()

        if name.name != self.name:
            self.logger.info(f"Setting telegram bot name to {self.name}")
            await self.bot.set_my_name(self.name)

    async def setup_telegram_bot_description(self) -> None:
        description = await self.bot.get_my_description()

        if description.description != self.description:
            self.logger.info(f"Setting telegram bot description to {self.description}")
            await self.bot.set_my_description(self.description)

    async def setup_telegram_bot_short_description(self) -> None:
        short_description = await self.bot.get_my_short_description()

        if short_description.short_description != self.short_description:
            self.logger.info(f"Setting telegram bot short description to {self.short_description}")
            await self.bot.set_my_short_description(self.short_description)

    async def setup_telegram_bot_commands(self) -> None:
        commands = await self.bot.get_my_commands()

        if commands != self.commands:
            self.logger.info(f"Setting telegram bot commands to {self.commands}")
            await self.bot.set_my_commands(self.commands)

    async def setup_telegram_webhook(self) -> None:
        if self.webhook is None:
            self.logger.info("Deleting telegram webhook")
            await self.bot.delete_webhook()
            return

        self.logger.info(f"Setting telegram webhook url to {self.webhook.url}")
        await self.bot.set_webhook(url=self.webhook.url, secret_token=self.webhook.secret_token)

    def get_startup_callbacks(self) -> list[lifecycle_utils.Callback]:
        return [
            lifecycle_utils.Callback(
                awaitable=self.setup_telegram_bot_name(),
                error_message="Failed to set telegram bot name",
                success_message="Telegram bot name has been set",
            ),
            lifecycle_utils.Callback(
                awaitable=self.setup_telegram_bot_description(),
                error_message="Failed to set telegram bot description",
                success_message="Telegram bot description has been set",
            ),
            lifecycle_utils.Callback(
                awaitable=self.setup_telegram_bot_short_description(),
                error_message="Failed to set telegram bot short description",
                success_message="Telegram bot short description has been set",
            ),
            lifecycle_utils.Callback(
                awaitable=self.setup_telegram_bot_commands(),
                error_message="Failed to set telegram bot commands",
                success_message="Telegram bot commands have been set",
            ),
            lifecycle_utils.Callback(
                awaitable=self.setup_telegram_webhook(),
                error_message="Failed to set telegram webhook",
                success_message="Telegram webhook has been set",
            ),
        ]

    def get_shutdown_callbacks(self) -> list[lifecycle_utils.Callback]:
        return [
            lifecycle_utils.Callback(
                awaitable=self.bot.session.close(),
                error_message="Failed to close telegram bot session",
                success_message="Telegram bot session has been closed",
            )
        ]

    def get_main_task(self) -> lifecycle_utils.Task:
        return asyncio.create_task(
            coro=self.dispatcher.start_polling(self.bot),
            name="aiogram_bot",
        )


__all__ = [
    "Lifecycle",
]
