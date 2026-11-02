import asyncio
import dataclasses
import datetime

import aiohttp.test_utils as aiohttp_test_utils
import aiohttp.web as aiohttp_web
import pytest

import lib.utils.aiohttp as aiohttp_utils


@dataclasses.dataclass
class FakeSubsystem:
    ready: bool = True
    error: Exception | None = None
    calls: int = 0

    async def is_ready(self) -> bool:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.ready


def create_service(
    *subsystems: aiohttp_utils.SubsystemReadinessCallback,
    ttl: datetime.timedelta = datetime.timedelta(seconds=10),
) -> aiohttp_utils.ReadinessService:
    return aiohttp_utils.ReadinessService(subsystems=list(subsystems), ttl=ttl)


@pytest.mark.asyncio
async def test_readiness_service_caches_statuses_within_ttl():
    subsystem = FakeSubsystem()
    service = create_service(aiohttp_utils.SubsystemReadinessCallback(name="database", is_ready=subsystem.is_ready))

    first_statuses = await service.get_statuses()
    subsystem.ready = False
    second_statuses = await service.get_statuses()

    assert subsystem.calls == 1
    assert second_statuses.statuses["database"] == first_statuses.statuses["database"]
    assert second_statuses.statuses["database"].value is True


@pytest.mark.asyncio
async def test_readiness_service_rechecks_statuses_after_ttl():
    subsystem = FakeSubsystem()
    service = create_service(
        aiohttp_utils.SubsystemReadinessCallback(name="database", is_ready=subsystem.is_ready),
        ttl=datetime.timedelta(0),
    )

    await service.get_statuses()
    subsystem.ready = False
    statuses = await service.get_statuses()

    assert subsystem.calls == 2
    assert statuses.statuses["database"].value is False


def test_readiness_service_rejects_duplicate_subsystem_names():
    subsystem = FakeSubsystem()

    with pytest.raises(ValueError):
        create_service(
            aiohttp_utils.SubsystemReadinessCallback(name="database", is_ready=subsystem.is_ready),
            aiohttp_utils.SubsystemReadinessCallback(name="database", is_ready=subsystem.is_ready),
        )


@pytest.mark.asyncio
async def test_readiness_service_checks_once_for_concurrent_requests():
    subsystem = FakeSubsystem()
    service = create_service(aiohttp_utils.SubsystemReadinessCallback(name="database", is_ready=subsystem.is_ready))

    await asyncio.gather(*(service.get_statuses() for _ in range(5)))

    assert subsystem.calls == 1


@pytest.mark.asyncio
async def test_readiness_service_reports_timed_out_subsystem_as_not_ready():
    async def hang() -> bool:
        await asyncio.sleep(10)
        return True

    service = aiohttp_utils.ReadinessService(
        subsystems=[aiohttp_utils.SubsystemReadinessCallback(name="database", is_ready=hang)],
        timeout=datetime.timedelta(milliseconds=10),
    )

    statuses = await service.get_statuses()

    assert statuses.statuses["database"].value is False


@pytest.mark.asyncio
async def test_readiness_service_treats_raising_subsystem_as_not_ready(caplog: pytest.LogCaptureFixture):
    subsystem = FakeSubsystem(error=RuntimeError("boom"))
    service = create_service(aiohttp_utils.SubsystemReadinessCallback(name="database", is_ready=subsystem.is_ready))

    statuses = await service.get_statuses()

    assert statuses.statuses["database"].value is False
    assert not statuses.is_readiness_ready()
    assert any(
        record.exc_info is not None and isinstance(record.exc_info[1], RuntimeError) for record in caplog.records
    )


@pytest.mark.asyncio
async def test_readiness_service_respects_required_flags():
    service = create_service(
        aiohttp_utils.SubsystemReadinessCallback(name="ready", is_ready=FakeSubsystem().is_ready),
        aiohttp_utils.SubsystemReadinessCallback(
            name="cache",
            is_ready=FakeSubsystem(ready=False).is_ready,
            readiness_required=False,
        ),
        aiohttp_utils.SubsystemReadinessCallback(
            name="warmup",
            is_ready=FakeSubsystem(ready=False).is_ready,
            startup_required=False,
        ),
    )

    statuses = await service.get_statuses()

    assert not statuses.is_readiness_ready()
    assert not statuses.is_startup_ready()
    assert statuses.statuses["cache"].readiness_required is False
    assert statuses.statuses["warmup"].startup_required is False


@pytest.mark.asyncio
async def test_readiness_service_ignores_not_required_subsystems():
    service = create_service(
        aiohttp_utils.SubsystemReadinessCallback(name="ready", is_ready=FakeSubsystem().is_ready),
        aiohttp_utils.SubsystemReadinessCallback(
            name="cache",
            is_ready=FakeSubsystem(ready=False).is_ready,
            readiness_required=False,
            startup_required=False,
        ),
    )

    statuses = await service.get_statuses()

    assert statuses.is_readiness_ready()
    assert statuses.is_startup_ready()


Client = aiohttp_test_utils.TestClient[aiohttp_web.Request, aiohttp_web.Application]


def create_client(readiness_service: aiohttp_utils.ReadinessService) -> Client:
    app = aiohttp_web.Application()
    app.router.add_get(
        "/health/readiness",
        aiohttp_utils.ReadinessProbeHandler(readiness_service=readiness_service).process,
    )
    app.router.add_get(
        "/health/startup",
        aiohttp_utils.StartupProbeHandler(readiness_service=readiness_service).process,
    )
    return aiohttp_test_utils.TestClient(aiohttp_test_utils.TestServer(app))


@pytest.mark.asyncio
async def test_probes_respond_healthy():
    service = create_service(
        aiohttp_utils.SubsystemReadinessCallback(name="database", is_ready=FakeSubsystem().is_ready),
        aiohttp_utils.SubsystemReadinessCallback(
            name="cache",
            is_ready=FakeSubsystem(ready=False).is_ready,
            readiness_required=False,
            startup_required=False,
        ),
    )

    async with create_client(service) as client:
        for path in ("/health/readiness", "/health/startup"):
            response = await client.get(path)

            assert response.status == 200
            assert await response.json() == {
                "status": "healthy",
                "subsystems_status": {
                    "database": {"value": True, "required": True},
                    "cache": {"value": False, "required": False},
                },
            }


@pytest.mark.asyncio
async def test_readiness_probe_responds_unhealthy():
    service = create_service(
        aiohttp_utils.SubsystemReadinessCallback(
            name="database",
            is_ready=FakeSubsystem(ready=False).is_ready,
            startup_required=False,
        ),
    )

    async with create_client(service) as client:
        readiness_response = await client.get("/health/readiness")
        startup_response = await client.get("/health/startup")

        assert readiness_response.status == 500
        assert await readiness_response.json() == {
            "status": "unhealthy",
            "subsystems_status": {"database": {"value": False, "required": True}},
        }
        assert startup_response.status == 200
        assert await startup_response.json() == {
            "status": "healthy",
            "subsystems_status": {"database": {"value": False, "required": False}},
        }


@pytest.mark.asyncio
async def test_startup_probe_responds_unhealthy():
    service = create_service(
        aiohttp_utils.SubsystemReadinessCallback(
            name="database",
            is_ready=FakeSubsystem(ready=False).is_ready,
            readiness_required=False,
        ),
    )

    async with create_client(service) as client:
        startup_response = await client.get("/health/startup")
        readiness_response = await client.get("/health/readiness")

        assert startup_response.status == 500
        assert await startup_response.json() == {
            "status": "unhealthy",
            "subsystems_status": {"database": {"value": False, "required": True}},
        }
        assert readiness_response.status == 200
        assert await readiness_response.json() == {
            "status": "healthy",
            "subsystems_status": {"database": {"value": False, "required": False}},
        }
