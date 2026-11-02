import asyncio
import contextlib
import logging
import socket

import aiohttp
import aiohttp.web as aiohttp_web
import pytest

import lib.utils.aiohttp as aiohttp_utils
import lib.utils.lifecycle as lifecycle_utils

logger = logging.getLogger(__name__)


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.asyncio
async def test_lifecycle_serves_liveness_probe():
    port = get_free_port()
    app = aiohttp_web.Application()
    app.router.add_get("/health/liveness", aiohttp_utils.LivenessProbeHandler().process)
    http_server_lifecycle = aiohttp_utils.Lifecycle(logger=logger, app=app, host="127.0.0.1", port=port)
    main_task = http_server_lifecycle.get_main_task()
    lifecycle = lifecycle_utils.Lifecycle(
        logger=logger,
        main_tasks=[main_task],
        startup_callbacks=http_server_lifecycle.get_startup_callbacks(),
        shutdown_callbacks=http_server_lifecycle.get_shutdown_callbacks(),
    )

    await lifecycle.on_startup()
    try:
        async with (
            aiohttp.ClientSession() as session,
            session.get(f"http://127.0.0.1:{port}/health/liveness") as response,
        ):
            assert response.status == 200
            assert await response.json() == {"status": "healthy"}
    finally:
        main_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await main_task
        await lifecycle.on_shutdown()


@pytest.mark.asyncio
async def test_lifecycle_fails_startup_on_busy_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        port = sock.getsockname()[1]
        http_server_lifecycle = aiohttp_utils.Lifecycle(
            logger=logger, app=aiohttp_web.Application(), host="127.0.0.1", port=port
        )
        lifecycle = lifecycle_utils.Lifecycle(
            logger=logger,
            startup_callbacks=http_server_lifecycle.get_startup_callbacks(),
            shutdown_callbacks=http_server_lifecycle.get_shutdown_callbacks(),
        )

        with pytest.raises(lifecycle_utils.Lifecycle.StartupError):
            await lifecycle.on_startup()
        await lifecycle.on_shutdown()
