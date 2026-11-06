from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.domain.exceptions import AuthenticationError

JWT_ALGORITHM = "HS256"


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = PasswordHash((Argon2Hasher(),))

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._hasher.verify(password, password_hash)


class JwtTokenService:
    def __init__(self, secret_key: str, expire_minutes: int) -> None:
        self._secret_key = secret_key
        self._expire_minutes = expire_minutes

    def create(self, student_id: int) -> str:
        expires_at = datetime.now(UTC) + timedelta(minutes=self._expire_minutes)
        return jwt.encode({"sub": str(student_id), "exp": expires_at}, self._secret_key, algorithm=JWT_ALGORITHM)

    def read_student_id(self, token: str) -> int:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]})
            return int(payload["sub"])
        except (jwt.InvalidTokenError, ValueError) as error:
            raise AuthenticationError("Token inválido o vencido") from error
