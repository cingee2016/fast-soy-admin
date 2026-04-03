"""Tests for Radar ORM models: RadarRequest, RadarQuery, RadarUserLog."""

from uuid import uuid4

import pytest

from app.system.radar.models import RadarQuery, RadarRequest, RadarUserLog

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _uid() -> str:
    return uuid4().hex[:12]


class TestRadarRequestModel:
    async def test_create_request(self, app):
        req = await RadarRequest.create(
            x_request_id=f"mdl-{_uid()}",
            method="GET",
            path="/api/v1/users",
            client_ip="127.0.0.1",
            query_params="page=1&size=10",
            request_headers={"content-type": "application/json"},
            response_status=200,
            response_body='{"code":"0000","msg":"OK","data":{}}',
            duration_ms=42.5,
        )
        assert req.id is not None
        assert req.method == "GET"
        assert req.path == "/api/v1/users"
        assert req.client_ip == "127.0.0.1"
        assert req.duration_ms == 42.5
        assert req.response_status == 200
        assert req.resolved is False

    async def test_unique_x_request_id(self, app):
        uid = f"mdl-uniq-{_uid()}"
        await RadarRequest.create(x_request_id=uid, method="GET", path="/a")
        with pytest.raises(Exception):
            await RadarRequest.create(x_request_id=uid, method="POST", path="/b")

    async def test_nullable_fields(self, app):
        req = await RadarRequest.create(
            x_request_id=f"mdl-null-{_uid()}",
            method="GET",
            path="/health",
        )
        assert req.client_ip is None
        assert req.query_params is None
        assert req.request_headers is None
        assert req.request_body is None
        assert req.response_status is None
        assert req.response_body is None
        assert req.duration_ms is None
        assert req.error_type is None
        assert req.error_message is None
        assert req.error_traceback is None

    async def test_error_fields(self, app):
        req = await RadarRequest.create(
            x_request_id=f"mdl-err-{_uid()}",
            method="POST",
            path="/api/v1/auth/login",
            response_status=500,
            error_type="ValueError",
            error_message="invalid credentials",
            error_traceback="Traceback ...",
        )
        assert req.error_type == "ValueError"
        assert req.error_message == "invalid credentials"
        assert req.error_traceback == "Traceback ..."
        assert req.response_status == 500

    async def test_to_dict_camel_case(self, app):
        uid = f"mdl-dict-{_uid()}"
        req = await RadarRequest.create(
            x_request_id=uid,
            method="GET",
            path="/api/v1/users",
            client_ip="127.0.0.1",
            duration_ms=42.5,
            response_status=200,
        )
        d = await req.to_dict()
        assert "xRequestId" in d
        assert "clientIp" in d
        assert "durationMs" in d
        assert "responseStatus" in d
        assert d["xRequestId"] == uid

    async def test_to_dict_include_fields(self, app):
        req = await RadarRequest.create(
            x_request_id=f"mdl-inc-{_uid()}",
            method="GET",
            path="/api/v1/users",
            client_ip="127.0.0.1",
        )
        d = await req.to_dict(include_fields=["x_request_id", "method", "path"])
        assert "xRequestId" in d
        assert "method" in d
        assert "path" in d
        assert "clientIp" not in d

    async def test_resolved_toggle(self, app):
        req = await RadarRequest.create(
            x_request_id=f"mdl-resolve-{_uid()}",
            method="POST",
            path="/crash",
            error_type="RuntimeError",
        )
        assert req.resolved is False
        req.resolved = True
        await req.save()
        refreshed = await RadarRequest.get(id=req.id)
        assert refreshed.resolved is True


class TestRadarQueryModel:
    async def test_create_query(self, app):
        req = await RadarRequest.create(x_request_id=f"mdl-q-{_uid()}", method="GET", path="/q")
        query = await RadarQuery.create(
            request=req,
            sql_text="SELECT * FROM users WHERE id = ?",
            params="[1]",
            operation="SELECT",
            duration_ms=5.3,
            connection_name="conn_system",
            start_offset_ms=10.0,
        )
        assert query.id is not None
        assert query.sql_text == "SELECT * FROM users WHERE id = ?"
        assert query.operation == "SELECT"
        assert query.duration_ms == 5.3

    async def test_query_request_relationship(self, app):
        req = await RadarRequest.create(x_request_id=f"mdl-qrel-{_uid()}", method="GET", path="/qrel")
        await RadarQuery.create(request=req, sql_text="SELECT 1", duration_ms=1.0)
        await RadarQuery.create(request=req, sql_text="SELECT 2", duration_ms=2.0)
        queries = await RadarQuery.filter(request=req).all()
        assert len(queries) == 2

    async def test_cascade_delete(self, app):
        req = await RadarRequest.create(x_request_id=f"mdl-casc-{_uid()}", method="GET", path="/cascade")
        await RadarQuery.create(request=req, sql_text="SELECT 1", duration_ms=1.0)
        await RadarQuery.create(request=req, sql_text="SELECT 2", duration_ms=2.0)

        assert await RadarQuery.filter(request=req).count() == 2
        req_id = req.id
        await req.delete()
        assert await RadarQuery.filter(request_id=req_id).count() == 0


class TestRadarUserLogModel:
    async def test_create_user_log(self, app):
        req = await RadarRequest.create(x_request_id=f"mdl-ul-{_uid()}", method="GET", path="/ul")
        log = await RadarUserLog.create(
            request=req,
            level="INFO",
            message="User logged in successfully",
            data='{"user_id": 1}',
            source="auth.login",
            offset_ms=20.0,
        )
        assert log.id is not None
        assert log.level == "INFO"
        assert log.message == "User logged in successfully"

    async def test_user_log_without_request(self, app):
        log = await RadarUserLog.create(
            level="WARNING",
            message=f"Standalone warning log {_uid()}",
        )
        assert log.id is not None

    async def test_user_log_levels(self, app):
        req = await RadarRequest.create(x_request_id=f"mdl-lvl-{_uid()}", method="GET", path="/lvl")
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            log = await RadarUserLog.create(request=req, level=level, message=f"Test {level}")
            assert log.level == level

    async def test_user_log_cascade_delete(self, app):
        req = await RadarRequest.create(x_request_id=f"mdl-ulc-{_uid()}", method="GET", path="/ulc")
        await RadarUserLog.create(request=req, level="INFO", message="test log")

        assert await RadarUserLog.filter(request=req).count() == 1
        req_id = req.id
        await req.delete()
        assert await RadarUserLog.filter(request_id=req_id).count() == 0
