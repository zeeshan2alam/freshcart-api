import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User
from security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    unauth = HTTPException(401, "Pehle login karein.", headers={"WWW-Authenticate": "Bearer"})
    if not creds:
        raise unauth
    try:
        data = decode_token(creds.credentials)
        user = db.get(User, int(data["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Session expire ho gaya, dobara login karein.", headers={"WWW-Authenticate": "Bearer"})
    if not user:
        raise unauth
    return user


def admin_only(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Sirf admin ye kar sakta hai.")
    return user
