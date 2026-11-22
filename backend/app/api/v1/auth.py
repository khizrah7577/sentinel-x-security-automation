"""Authentication endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends

from app.core.deps import CurrentUser, DbSession
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserActivity
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login_json(payload: LoginRequest, db: DbSession):
    return _login(db, payload.email, payload.password)


@router.post("/login/form", response_model=TokenResponse)
def login_form(db: DbSession, form: OAuth2PasswordRequestForm = Depends()):
    # OAuth2 form uses "username" field for email
    return _login(db, form.username, form.password)


def _login(db: DbSession, email: str, password: str) -> TokenResponse:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    user.last_login_at = datetime.now(timezone.utc)
    db.add(UserActivity(user_id=user.id, action="login", detail="Successful login"))
    db.commit()
    token = create_access_token(subject=user.email, extra={"role": user.role.value})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/logout")
def logout(user: CurrentUser, db: DbSession):
    db.add(UserActivity(user_id=user.id, action="logout", detail="Logout"))
    db.commit()
    return {"message": "Logged out"}
