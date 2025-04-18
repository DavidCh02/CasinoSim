from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Boolean, ForeignKey, Date
from sqlalchemy.sql import func
from database import Base  # Importamos Base desde database.py

# Modelo de usuario
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    fecha_creacion = Column(DateTime, server_default=func.now())
    dinero_efectivo = Column(DECIMAL(10,2), default=5.00)
    dinero_banco = Column(DECIMAL(10,2), default=0.00)
    avatar_url = Column(String(200), nullable=False)

class Factura(Base):
    __tablename__ = 'facturas'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tipo = Column(String(20), nullable=False)
    monto = Column(DECIMAL(10,2), nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    pagado = Column(Boolean, default=False)