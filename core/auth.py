from ninja.security import HttpBearer


class BearerAuth(HttpBearer):
    """Bearer token authentication for Matrix API access."""

    def authenticate(self, request, token):
        return token
