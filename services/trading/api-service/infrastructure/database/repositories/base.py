"""Base repository with common CRUD operations"""

from abc import ABC
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from uuid import UUID

from sqlalchemy import and_, or_, select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from infrastructure.database.models.base import Base


# Generic type for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType], ABC):
    """Base repository with common CRUD operations for SQLAlchemy models"""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, obj_data: Dict[str, Any]) -> ModelType:
        """Create a new instance"""
        db_obj = self.model(**obj_data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def get(self, id: Union[str, UUID]) -> Optional[ModelType]:
        """Get instance by ID"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == str(id))
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
    ) -> List[ModelType]:
        """Get multiple instances with pagination and filtering"""
        query = select(self.model)

        # Apply filters
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        conditions.append(getattr(self.model, field).in_(value))
                    else:
                        conditions.append(getattr(self.model, field) == value)
            if conditions:
                query = query.where(and_(*conditions))

        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
                field = order_by[1:]
                if hasattr(self.model, field):
                    query = query.order_by(getattr(self.model, field).desc())
            else:
                if hasattr(self.model, order_by):
                    query = query.order_by(getattr(self.model, order_by))
        else:
            # Default ordering by created_at descending
            query = query.order_by(self.model.created_at.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(
        self, id: Union[str, UUID], obj_data: Dict[str, Any]
    ) -> Optional[ModelType]:
        """Update instance by ID"""
        # Remove None values to avoid overwriting with null
        update_data = {k: v for k, v in obj_data.items() if v is not None}

        if not update_data:
            return await self.get(id)

        result = await self.session.execute(
            update(self.model)
            .where(self.model.id == str(id))
            .values(**update_data)
            .returning(self.model)
        )
        updated_obj = result.scalar_one_or_none()

        if updated_obj:
            await self.session.refresh(updated_obj)

        return updated_obj

    async def delete(self, id: Union[str, UUID]) -> bool:
        """Delete instance by ID"""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == str(id))
        )
        return result.rowcount > 0

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count instances with optional filtering"""
        query = select(func.count(self.model.id))

        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        conditions.append(getattr(self.model, field).in_(value))
                    else:
                        conditions.append(getattr(self.model, field) == value)
            if conditions:
                query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def exists(self, id: Union[str, UUID]) -> bool:
        """Check if instance exists by ID"""
        result = await self.session.execute(
            select(func.count(self.model.id)).where(self.model.id == str(id))
        )
        return (result.scalar() or 0) > 0

    async def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """Get instance by a specific field"""
        if not hasattr(self.model, field):
            return None

        result = await self.session.execute(
            select(self.model).where(getattr(self.model, field) == value)
        )
        return result.scalar_one_or_none()

    async def get_multi_by_field(
        self, field: str, value: Any, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple instances by a specific field"""
        if not hasattr(self.model, field):
            return []

        query = (
            select(self.model)
            .where(getattr(self.model, field) == value)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def bulk_create(self, objects_data: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple instances in bulk"""
        db_objs = [self.model(**obj_data) for obj_data in objects_data]
        self.session.add_all(db_objs)
        await self.session.flush()

        # Refresh all objects to get generated fields
        for obj in db_objs:
            await self.session.refresh(obj)

        return db_objs

    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Update multiple instances in bulk"""
        if not updates:
            return 0

        # Group updates by ID
        for update_data in updates:
            if "id" not in update_data:
                continue

            obj_id = update_data.pop("id")
            if update_data:  # Only update if there's data
                await self.session.execute(
                    update(self.model)
                    .where(self.model.id == str(obj_id))
                    .values(**update_data)
                )

        return len(updates)

    async def soft_delete(self, id: Union[str, UUID]) -> bool:
        """Soft delete instance (if model supports it)"""
        if hasattr(self.model, "is_deleted"):
            result = await self.session.execute(
                update(self.model)
                .where(self.model.id == str(id))
                .values(is_deleted=True)
            )
            return result.rowcount > 0
        else:
            # Fallback to hard delete
            return await self.delete(id)

    def _build_query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
    ) -> Select:
        """Build base query with common filtering and search"""
        query = select(self.model)

        # Apply filters
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        conditions.append(getattr(self.model, field).in_(value))
                    elif isinstance(value, dict):
                        # Support for range queries: {"gte": 100, "lte": 200}
                        column = getattr(self.model, field)
                        if "gte" in value:
                            conditions.append(column >= value["gte"])
                        if "lte" in value:
                            conditions.append(column <= value["lte"])
                        if "gt" in value:
                            conditions.append(column > value["gt"])
                        if "lt" in value:
                            conditions.append(column < value["lt"])
                    else:
                        conditions.append(getattr(self.model, field) == value)
            if conditions:
                query = query.where(and_(*conditions))

        # Apply search
        if search and search_fields:
            search_conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    if (
                        hasattr(column.type, "python_type")
                        and column.type.python_type == str
                    ):
                        search_conditions.append(column.ilike(f"%{search}%"))
            if search_conditions:
                query = query.where(or_(*search_conditions))

        return query
