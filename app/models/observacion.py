import uuid
from sqlalchemy import Column, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base

class Observacion(Base):
    __tablename__ = "observaciones"

    id_observacion = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    id_alumno = Column(UUID(as_uuid=True), ForeignKey("alumnos.id_alumno", ondelete="CASCADE"), nullable=False)
    id_autor = Column(UUID(as_uuid=True), ForeignKey("personas.id_persona", ondelete="RESTRICT"), nullable=False)

    texto = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    alumno = relationship("Alumno", back_populates="observaciones")
    autor = relationship("Persona")
