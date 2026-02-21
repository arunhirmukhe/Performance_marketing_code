"""Authentication service - business logic for user management."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.utils.security import hash_password, verify_password, create_access_token


class AuthService:
    """Handles user authentication business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(self, email: str, password: str, full_name: str) -> User:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    def authenticate(self, user: User, password: str) -> bool:
        return verify_password(password, user.hashed_password)

    @staticmethod
    def generate_token(user_id: str) -> str:
        return create_access_token(user_id)
