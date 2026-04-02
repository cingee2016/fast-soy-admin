from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import SchemaBase


class CredentialsSchema(SchemaBase):
    user_name: str | None = Field(None, title="用户名")
    password: str | None = Field(None, title="密码")


class JWTOut(SchemaBase):
    access_token: str | None = Field(None, alias="token", title="请求token")
    refresh_token: str | None = Field(None, title="刷新token")


class JWTPayload(BaseModel):
    data: dict
    iat: datetime
    exp: datetime


class CaptchaRequest(SchemaBase):
    phone: str = Field(title="手机号")


class CodeLoginSchema(SchemaBase):
    phone: str = Field(title="手机号")
    code: str = Field(title="验证码")


class RegisterSchema(SchemaBase):
    phone: str = Field(title="手机号")
    code: str = Field(title="验证码")
    password: str = Field(title="密码")
    user_name: str | None = Field(None, title="用户名")


__all__ = ["CredentialsSchema", "JWTOut", "JWTPayload", "CaptchaRequest", "CodeLoginSchema", "RegisterSchema"]
