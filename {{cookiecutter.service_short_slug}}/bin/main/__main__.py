import asyncio
import logging
import os

import lib.app as app

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = app.Settings()
    try:
        application = app.Application.from_settings(settings)
    except Exception as exc:
        logger.exception("Failed to initialize application settings")
        raise app.ServerStartError("Failed to initialize application settings") from exc

    try:
        await application.start()
    finally:
        await application.dispose()


def main() -> None:
    try:
        asyncio.run(run())
        exit(os.EX_OK)
    except SystemExit:
        exit(os.EX_OK)
    except app.ApplicationError:
        exit(os.EX_SOFTWARE)
    except KeyboardInterrupt:
        logger.info("Exited with keyboard interruption")
        exit(os.EX_OK)
    except BaseException:
        logger.exception("Unexpected error occurred")
        exit(os.EX_SOFTWARE)


if __name__ == "__main__":
    main()
