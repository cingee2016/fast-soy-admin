from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel
from tortoise.expressions import Q

AuthMode = Literal["permission", "auth", "public"]
EventDelivery = Literal["local", "outbox"]
ModuleSource = Literal["manifest", "legacy"]
PolicyAction = Literal["read", "get", "create", "update", "delete"]

_MODULE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_POLICY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


@dataclass(slots=True)
class BusinessRouter:
    """Router declared by a business module manifest."""

    router: APIRouter
    prefix: str = ""
    auth: AuthMode = "permission"
    tags: Sequence[str | Enum] | None = None

    def __post_init__(self) -> None:
        if self.auth not in {"permission", "auth", "public"}:
            raise ValueError("BusinessRouter.auth must be one of: permission, auth, public")
        if self.prefix and not self.prefix.startswith("/"):
            self.prefix = f"/{self.prefix}"
        if self.prefix != "/" and self.prefix.endswith("/"):
            self.prefix = self.prefix.rstrip("/")


@dataclass(slots=True)
class PermissionSpec:
    """Permission declarations owned by a business module."""

    init_data: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class EventSpec:
    """Typed event contract for local or future outbox delivery."""

    name: str
    payload: type[BaseModel] | None = None
    version: int = 1
    delivery: EventDelivery = "local"

    def __post_init__(self) -> None:
        if not _EVENT_NAME_RE.match(self.name):
            raise ValueError(f"Invalid event name: {self.name!r}")
        if self.version < 1:
            raise ValueError("EventSpec.version must be >= 1")
        if self.delivery not in {"local", "outbox"}:
            raise ValueError("EventSpec.delivery must be one of: local, outbox")


@dataclass(slots=True)
class PolicyContext:
    """Runtime context passed to business data policies."""

    user_id: int | None
    role_codes: list[str]
    button_codes: list[str]
    is_super: bool
    redis: Any | None = None
    module: str | None = None


PolicyFilterBuilder = Callable[[PolicyContext], Q | Awaitable[Q]]
PolicyObjectChecker = Callable[[PolicyContext, Any], bool | Awaitable[bool]]
TaskHandler = Callable[[], None | Awaitable[None]]


@dataclass(frozen=True, slots=True)
class DataPolicy:
    """Business-owned data policy.

    Read policies may provide a Tortoise Q filter. Object-level policies may
    provide a checker that receives the target object.
    """

    name: str
    action: PolicyAction = "read"
    build_filter: PolicyFilterBuilder | None = None
    check_object: PolicyObjectChecker | None = None
    model: Any | None = None

    def __post_init__(self) -> None:
        if not _POLICY_NAME_RE.match(self.name):
            raise ValueError(f"Invalid data policy name: {self.name!r}")
        if self.action not in {"read", "get", "create", "update", "delete"}:
            raise ValueError("Invalid data policy action")
        if self.build_filter is None and self.check_object is None:
            raise ValueError("DataPolicy requires build_filter or check_object")


@dataclass(frozen=True, slots=True)
class PeriodicTask:
    """Periodic task declared by a business module manifest."""

    name: str
    handler: TaskHandler
    interval_seconds: int
    leader_only: bool = True
    run_immediately: bool = False

    def __post_init__(self) -> None:
        if not _POLICY_NAME_RE.match(self.name):
            raise ValueError(f"Invalid task name: {self.name!r}")
        if self.interval_seconds <= 0:
            raise ValueError("PeriodicTask.interval_seconds must be > 0")


@dataclass(slots=True)
class BusinessModule:
    """Business module manifest.

    New modules should export `module = BusinessModule(...)` from
    `app/business/<name>/module.py`. Legacy modules without a manifest keep the
    existing file-convention based autodiscovery behavior.
    """

    name: str
    title: str | None = None
    version: str = "0.1.0"
    depends_on: Sequence[str] = field(default_factory=list)
    router: APIRouter | None = None
    routers: Sequence[BusinessRouter] = field(default_factory=list)
    init: Callable[[], Awaitable[None]] | None = None
    permissions: PermissionSpec | None = None
    events: Sequence[EventSpec] = field(default_factory=list)
    data_policies: Sequence[DataPolicy] = field(default_factory=list)
    tasks: Sequence[PeriodicTask] = field(default_factory=list)
    source: ModuleSource = field(default="manifest", init=False)

    def __post_init__(self) -> None:
        if not _MODULE_NAME_RE.match(self.name):
            raise ValueError(f"Invalid business module name: {self.name!r}")
        if self.router is not None and self.routers:
            raise ValueError("Use either BusinessModule.router or BusinessModule.routers, not both")
        if self.router is not None:
            self.routers = [BusinessRouter(router=self.router)]
            self.router = None
        else:
            self.routers = list(self.routers)
        self.depends_on = list(dict.fromkeys(self.depends_on))
        self.events = list(self.events)
        self.data_policies = list(self.data_policies)
        self.tasks = list(self.tasks)
        if self.title is None:
            self.title = self.name
