import uuid
from sqlalchemy import Column, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base

class Alumno(Base):
    __tablename__ = "alumnos"

    id_alumno = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_persona = Column(UUID(as_uuid=True), ForeignKey("personas.id_persona", ondelete="CASCADE"), unique=True, nullable=False)

    dias_disponibles = Column(JSONB)
    franja_horaria = Column(String)
    motivo_oracion = Column(String(300))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    observaciones = relationship("Observacion", back_populates="alumno", cascade="all, delete-orphan")
