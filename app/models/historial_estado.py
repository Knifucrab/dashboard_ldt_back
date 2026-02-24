import uuid
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database.base import Base

class HistorialEstado(Base):
    __tablename__ = "historial_estados"

    id_historial = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    id_alumno = Column(UUID(as_uuid=True), ForeignKey("alumnos.id_alumno", ondelete="CASCADE"), nullable=False)
    id_estado = Column(Integer, ForeignKey("estados.id_estado"), nullable=False)

    comentario = Column(String(500))  # Cambiado de 'titulo' a 'comentario' para coincidir con la BD
    fecha_cambio = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cambiado_por = Column(UUID(as_uuid=True), ForeignKey("personas.id_persona"))
