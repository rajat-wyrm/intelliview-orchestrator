from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from orchestrator.auth import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Validate the JWT and return the current user.
    """
    payload = verify_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return payload

def require_role(role: str):
    """
    Restrict access to users with a specific role.
    """

    def checker(user=Depends(get_current_user)):
        if user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return user

    return checker
