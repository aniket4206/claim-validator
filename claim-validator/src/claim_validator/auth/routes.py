"""Authentication API routes — login, logout, create user, me, change password."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from claim_validator.auth.schemas import (
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    UserResponse,
)
from claim_validator.auth.utils import (
    TOKEN_EXPIRY,
    create_token,
    get_token_from_request,
    hash_password,
    revoke_token,
    verify_password,
    verify_token,
)
from claim_validator.db.session import SessionLocal
from claim_validator.db.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/create-user", response_model=UserResponse)
def create_user(req: CreateUserRequest):
    """Create a new user (admin only in production, open for now)."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == req.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            first_name=req.first_name,
            last_name=req.last_name,
            email=req.email,
            password_hash=hash_password(req.password),
            role=req.role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return UserResponse.model_validate(user)
    finally:
        db.close()


@router.post("/login")
def login(req: LoginRequest):
    """Authenticate user with email + password, set auth cookie."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == req.email, User.is_active == True).first()

        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        display_name = f"{user.first_name} {user.last_name}"
        token = create_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            display_name=display_name,
        )

        response = JSONResponse({
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "display_name": display_name,
            },
        })
        response.set_cookie(
            key="auth_token",
            value=token,
            max_age=TOKEN_EXPIRY,
            httponly=False,
            samesite="lax",
            path="/",
        )
        return response
    finally:
        db.close()


@router.post("/logout")
def logout(request: Request):
    """Invalidate the current token and clear the auth cookie."""
    token = get_token_from_request(request)
    if token:
        revoke_token(token)
    response = JSONResponse({"status": "ok"})
    response.delete_cookie("auth_token", path="/")
    return response


@router.get("/me")
def me(request: Request):
    """Return current user info from token."""
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = verify_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Token expired")
    return {
        "id": data["user_id"],
        "email": data["email"],
        "role": data["role"],
        "display_name": data["display_name"],
    }


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, request: Request):
    """Change the current user's password."""
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = verify_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Token expired")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == data["user_id"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not verify_password(req.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        user.password_hash = hash_password(req.new_password)
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()
