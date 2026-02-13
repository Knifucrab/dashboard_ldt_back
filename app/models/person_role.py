from sqlalchemy import Column, SmallInteger, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database.base import Base

class PersonRole(Base):
    __tablename__ = "person_roles"

    person_id = Column(UUID(as_uuid=True), ForeignKey("personas.id_persona", ondelete="CASCADE"), primary_key=True, nullable=False)
    id_rol = Column(SmallInteger, ForeignKey("roles.id_rol", ondelete="CASCADE"), primary_key=True, nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
