from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import create_token, hash_password, verify_password
from app.core.database import get_cursor
from app.core.deps import get_current_user
from app.models.user import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest):
    with get_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE username = %s", (body.username,))
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已被注册",
            )
        password_hash = hash_password(body.password)
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (body.username, password_hash),
        )
        user_id = cur.lastrowid

    token = create_token(user_id, body.username)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user_id, username=body.username),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (body.username,),
        )
        row = cur.fetchone()
        if not row or not verify_password(body.password, row[2]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )
        user_id, username = row[0], row[1]

    token = create_token(user_id, username)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user_id, username=username),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(id=current_user["user_id"], username=current_user["username"])
