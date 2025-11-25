import time
import jwt

JWT_PW = "Kai hat den richtigen Schlüssel"  # GEHEIMER SCHLÜSSEL – identical auf allen Servern!
JWT_ALGORITHMUS = "HS256"
JWT_LIFETIME_SECONDS = 300  # 5 Minuten gültig

def create_jwt(user_id: int) -> str:
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + JWT_LIFETIME_SECONDS,
    }
    token = jwt.encode(payload, JWT_PW, algorithm=JWT_ALGORITHMUS)
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

def decode_jwt(token: str) -> dict:
    daten = jwt.decode(token, JWT_PW, algorithms=[JWT_ALGORITHMUS])
    return daten
