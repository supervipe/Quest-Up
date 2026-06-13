from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_token_pair, hash_password, verify_password
from app.models.avatar import UserAvatar
from app.models.user import User, UserProfile, UserStats


async def register_user(db: AsyncSession, email: str, password: str, display_name: str) -> tuple[User, str, str]:
    existing = await db.scalar(select(User).where(User.email == email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=email.lower(), password_hash=hash_password(password), display_name=display_name.strip())
    db.add(user)
    await db.flush()
    db.add_all([UserProfile(user_id=user.id), UserStats(user_id=user.id), UserAvatar(user_id=user.id)])
    await db.commit()
    await db.refresh(user)
    access_token, refresh_token = create_token_pair(user.id)
    return user, access_token, refresh_token


async def login_user(db: AsyncSession, email: str, password: str) -> tuple[User, str, str]:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    access_token, refresh_token = create_token_pair(user.id)
    return user, access_token, refresh_token
