import contextvars
import time
from dataclasses import dataclass, field


@dataclass
class RadarRequestContext:
    x_request_id: str
    start_mono: float = field(default_factory=time.monotonic)
    method: str = ""
    path: str = ""
    query_params: str | None = None
    request_headers: dict | None = None
    request_body: str | None = None
    response_status: int | None = None
    response_headers: dict | None = None
    response_body: str | None = None
    queries: list[dict] = field(default_factory=list)
    user_logs: list[dict] = field(default_factory=list)
    exception_info: dict | None = None


CTX_RADAR: contextvars.ContextVar[RadarRequestContext | None] = contextvars.ContextVar("radar_context", default=None)
