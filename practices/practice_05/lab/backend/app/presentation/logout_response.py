from fastapi import Request, Response


def is_logout(request: Request) -> bool:
    return request.url.path == "/v1/auth/logout"


def logout_policy(
        request: Request,
        response: Response,
        *,
        authentication_failure: bool = False) -> Response:
    if not is_logout(request):
        return response
    response.headers["Cache-Control"] = "no-store"
    credential_check = getattr(
        request.state, "logout_credential_check", False,
    )
    if response.status_code == 204 or (
        authentication_failure and credential_check
    ):
        response.delete_cookie(
            "session_token", path="/", secure=True,
            httponly=True, samesite="lax",
        )
    if request.method == "HEAD":
        response.body = b""
        response.headers["content-length"] = "0"
    return response
