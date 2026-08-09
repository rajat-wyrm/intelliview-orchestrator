from sqlalchemy import Column, String, DateTime
from database.models._base import Base, utcnow


class User(Base):
    """
    User ORM Model
    Represents a registered user (admin, hr, etc.) who can access the dashboard.
    """

    __tablename__ = "users"

    user_id = Column(String(255), primary_key=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', email='{self.email}', role='{self.role}')>"
