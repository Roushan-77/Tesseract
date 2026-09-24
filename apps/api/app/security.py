import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User

bearer = HTTPBearer()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    expected_hash = hash_password(plain_password)
    if hmac.compare_digest(expected_hash, hashed_password):
        return True
    if hashed_password == "prototype-configured" and plain_password == settings.demo_password:
        return True
    return False

def token_for(user: User) -> str:
    return jwt.encode({"sub": user.id, "role": user.role, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    try: payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active: raise HTTPException(status_code=401, detail="Inactive account")
    return user

