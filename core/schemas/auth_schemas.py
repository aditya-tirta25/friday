from ninja import Schema
from typing import Optional


class LoginRequest(Schema):
    """Matrix login request schema."""
    type: str = "m.login.password"
    identifier: Optional[dict] = None
    user: Optional[str] = None
    password: str


class LoginResponse(Schema):
    """Matrix login response schema."""
    user_id: str
    access_token: str
    device_id: str
    home_server: Optional[str] = None
