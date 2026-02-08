from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
	DATABASE_URL,
	pool_pre_ping=True,
	connect_args={"sslmode": "require"}
)

# Session factory for dependencies
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base is in base.py
from .base import Base

