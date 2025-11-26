"""Base SQLAlchemy model with common fields"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    declarative_base as orm_declarative_base,
)
from sqlalchemy.dialects.postgresql import UUID


class BaseModel:
    """Base model with common fields and methods"""

    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="Unique identifier",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp",
    )

    def __init__(self, **kwargs):
        """Initialize model with default values for testing"""
        # Set default ID if not provided
        if "id" not in kwargs:
            self.id = str(uuid4())

        # Set default timestamps if not provided
        now = datetime.now()
        if "created_at" not in kwargs:
            self.created_at = now
        if "updated_at" not in kwargs:
            self.updated_at = now

        # Set other attributes from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """String representation"""
        return f"<{self.__class__.__name__}(id={self.id})>"


# Create declarative base using SQLAlchemy 2.0 syntax
Base = orm_declarative_base(cls=BaseModel)
