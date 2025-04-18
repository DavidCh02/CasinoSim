from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import ssl

# PostgreSQL database URL with pg8000 driver
DATABASE_URL = "postgresql+pg8000://casinosim_user:V9R7r7DcpOyri6gVcthAroHdiYH5nFov@dpg-cvsvolc9c44c73c7ubr0-a.oregon-postgres.render.com/casinosim"

try:
    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    engine = create_engine(
        DATABASE_URL,
        echo=True,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={
            "ssl_context": ssl_context
        }
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

    # Import models here to avoid circular imports
    from models import User, Factura

    # Create all tables
    Base.metadata.create_all(bind=engine)
    
except Exception as e:
    print(f"Error initializing database: {e}")
    raise

@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        print(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        session.close()