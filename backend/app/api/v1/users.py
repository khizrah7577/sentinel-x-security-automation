"""User management (admin)."""

from fastapi import APIRouter, HTTPException, status

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.core.security import get_password_hash
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(_: AdminUser, db: DbSession):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, admin: AdminUser, db: DbSession):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="user.create",
            resource_type="user",
            detail=f"Created {payload.email}",
            success=True,
        )
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, admin: AdminUser, db: DbSession):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        user.hashed_password = get_password_hash(data.pop("password"))
    for key, value in data.items():
        setattr(user, key, value)
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="user.update",
            resource_type="user",
            resource_id=str(user_id),
            success=True,
        )
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/me/profile", response_model=UserOut)
def my_profile(user: CurrentUser):
    return user
