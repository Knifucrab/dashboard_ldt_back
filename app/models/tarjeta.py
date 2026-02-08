import uuid
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database.base import Base

class Tarjeta(Base):
    __tablename__ = "tarjetas"

    id_tarjeta = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    id_alumno = Column(UUID(as_uuid=True), ForeignKey("alumnos.id_alumno", ondelete="CASCADE"), unique=True, nullable=False)
    id_estado_actual = Column(ForeignKey("estados.id_estado"), nullable=False)
    id_maestro_asignado = Column(UUID(as_uuid=True), ForeignKey("maestros.id_maestro"))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
