from ninja import Router
from ninja.errors import HttpError

from core.schemas import LoginResponse
from core.services import MatrixService

router = Router()


@router.post("/login", response=LoginResponse)
def matrix_login(request):
    """
    Login to Matrix homeserver using configured credentials.

    Returns an access token for the configured Matrix service account.
    """
    matrix_service = MatrixService()

    try:
        result = matrix_service.login()

        return LoginResponse(
            user_id=result['user_id'],
            access_token=result['access_token'],
            device_id=result['device_id'],
            home_server=result.get('home_server'),
        )
    except Exception as e:
        raise HttpError(401, f"Login failed: {str(e)}")
