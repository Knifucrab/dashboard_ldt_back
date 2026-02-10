from sqlalchemy import Column, SmallInteger, Text, DateTime
from sqlalchemy.sql import func
from app.database.base import Base

class Role(Base):
    __tablename__ = "roles"

    id_rol = Column(SmallInteger, primary_key=True)
    descripcion = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
