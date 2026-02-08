from sqlalchemy import Column, SmallInteger, Integer, Text, DateTime
from sqlalchemy.sql import func
from database.base import Base

class Profile(Base):
    __tablename__ = "perfiles"

    id_perfil = Column(SmallInteger, primary_key=True)
    descripcion = Column(Text, nullable=False)
    nivel_acceso = Column(Integer, nullable=False) # 1: Admin, 2: Moderator, 3: User
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
