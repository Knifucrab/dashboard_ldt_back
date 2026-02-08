import uuid
from sqlalchemy import Column, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database.base import Base

class Maestro(Base):
    __tablename__ = "maestros"

    id_maestro = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_persona = Column(UUID(as_uuid=True), ForeignKey("personas.id_persona", ondelete="CASCADE"), unique=True, nullable=False)

    telefono = Column(String)
    direccion = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
