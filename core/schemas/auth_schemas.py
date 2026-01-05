from ninja import Schema
from typing import Optional


class LoginResponse(Schema):
    """Matrix login response schema."""
    user_id: str
    access_token: str
    device_id: str
    home_server: Optional[str] = None
