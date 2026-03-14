from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("DB_USER")
PASSWORD = os.getenv("DB_PASSWORD")
HOST = os.getenv("DB_HOST")
PORT = os.getenv("DB_PORT")
DBNAME = os.getenv("DB_DBNAME")

# Construct the SQLAlchemy connection string
# DATABASESQLALCHEMY_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
# That above format DATABASESQLALCHEMY_URL has already saved into env file
DATABASESQLALCHEMY_URL = os.getenv("DATABASESQLALCHEMY_URL")

# Create the SQLAlchemy engine
# engine = create_engine(DATABASESQLALCHEMY_URL)
# If using Transaction Pooler or Session Pooler, we want to ensure we disable SQLAlchemy client side pooling -
# https://docs.sqlalchemy.org/en/20/core/pooling.html#switching-pool-implementations
engine = create_engine(DATABASESQLALCHEMY_URL, poolclass=NullPool,  pool_pre_ping=True, pool_recycle=120) #15 mar 2026 pool_pre_ping to ensure test the connection before using it, pool_recycle to refresh connection every 2 minutes

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True
)

# Base class for models (2.0 style)
class Base(DeclarativeBase):
    pass

# Test the connection
try:
    with engine.connect() as connection:
        print("Connection successful!")
except Exception as e:
    print(f"Failed to connect: {e}")
