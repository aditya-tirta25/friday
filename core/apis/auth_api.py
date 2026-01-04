from ninja import Router
from ninja.errors import HttpError

from core.schemas import LoginRequest, LoginResponse
from core.services import MatrixService

router = Router()


@router.post("/login", response=LoginResponse)
def matrix_login(request, payload: LoginRequest):
    """
    Login to Matrix homeserver.

    This endpoint proxies the Matrix login API and returns an access token.
    """
    matrix_service = MatrixService()

    try:
        username = payload.user
        if payload.identifier and payload.identifier.get('user'):
            username = payload.identifier['user']

        result = matrix_service.login(
            username=username,
            password=payload.password
        )

        return LoginResponse(
            user_id=result['user_id'],
            access_token=result['access_token'],
            device_id=result['device_id'],
            home_server=result.get('home_server'),
        )
    except Exception as e:
        raise HttpError(401, f"Login failed: {str(e)}")
