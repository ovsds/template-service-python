import asyncio
import dataclasses
import datetime
import logging
import time
import typing

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class SubsystemReadinessCallback:
    name: str
    is_ready: typing.Callable[[], typing.Awaitable[bool]]
    readiness_required: bool = True
    startup_required: bool = True


@dataclasses.dataclass(frozen=True)
class SubsystemStatus:
    value: bool
    readiness_required: bool
    startup_required: bool
    checked_at: float


@dataclasses.dataclass(frozen=True)
class SubsystemStatuses:
    statuses: typing.Mapping[str, SubsystemStatus]

    def is_startup_ready(self) -> bool:
        return all(status.value for status in self.statuses.values() if status.startup_required)

    def is_readiness_ready(self) -> bool:
        return all(status.value for status in self.statuses.values() if status.readiness_required)


@dataclasses.dataclass(frozen=True)
class ReadinessService:
    subsystems: typing.Sequence[SubsystemReadinessCallback]
    ttl: datetime.timedelta = datetime.timedelta(seconds=10)
    timeout: datetime.timedelta = datetime.timedelta(seconds=5)
    _cache: dict[str, SubsystemStatus] = dataclasses.field(default_factory=dict[str, SubsystemStatus], init=False)
    _lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        names = [subsystem.name for subsystem in self.subsystems]
        if len(names) != len(set(names)):
            raise ValueError(f"Subsystem names must be unique, got {names}")

    async def get_statuses(self) -> SubsystemStatuses:
        async with self._lock:
            now = time.monotonic()
            stale_subsystems = [subsystem for subsystem in self.subsystems if self._is_stale(subsystem, now)]
            checked_statuses = await asyncio.gather(*(self._check(subsystem) for subsystem in stale_subsystems))
            for subsystem, status in zip(stale_subsystems, checked_statuses, strict=True):
                self._cache[subsystem.name] = status

            statuses = {subsystem.name: self._cache[subsystem.name] for subsystem in self.subsystems}
        return SubsystemStatuses(statuses=statuses)

    def _is_stale(self, subsystem: SubsystemReadinessCallback, now: float) -> bool:
        status = self._cache.get(subsystem.name)
        return status is None or now - status.checked_at >= self.ttl.total_seconds()

    async def _check(self, subsystem: SubsystemReadinessCallback) -> SubsystemStatus:
        try:
            async with asyncio.timeout(self.timeout.total_seconds()):
                value = await subsystem.is_ready()
        except TimeoutError:
            logger.error("Subsystem %s readiness check has timed out", subsystem.name)
            value = False
        except Exception:
            logger.exception("Subsystem %s readiness check has failed", subsystem.name)
            value = False

        return SubsystemStatus(
            value=value,
            readiness_required=subsystem.readiness_required,
            startup_required=subsystem.startup_required,
            checked_at=time.monotonic(),
        )


__all__ = [
    "ReadinessService",
    "SubsystemReadinessCallback",
    "SubsystemStatus",
    "SubsystemStatuses",
]
