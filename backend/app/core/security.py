from datetime import datetime, timedelta, timezone
import bcrypt
from jose import JWTError, jwt
from app.core.config import get_settings

settings = get_settings()
ALGORITHM = "HS256"


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def create_reset_token(user_id: str) -> str:
    """15-minute JWT with purpose='reset'."""
    return jwt.encode(
        {"sub": user_id, "purpose": "reset", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_reset_token(token: str) -> str | None:
    """Decode and validate a reset token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None
