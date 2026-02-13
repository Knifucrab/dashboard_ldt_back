import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database.base import Base

class Persona(Base):
    __tablename__ = "personas"

    id_persona = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_user_id = Column(UUID(as_uuid=True), unique=True, nullable=False)

    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    email = Column(String)
    password = Column(String, nullable=True)
    foto_url = Column(String)

    id_perfil = Column(ForeignKey("perfiles.id_perfil"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
