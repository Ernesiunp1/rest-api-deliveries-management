
from db.db import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Enum, Boolean, Text
from sqlalchemy.orm import relationship
import datetime

from schemas.schemas import (DeliveryStanding, UserRole, PaymentType,
                             PaymentStatus, SettlementStatus, AccountType)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole, name="user_role"), default = UserRole.RIDER)
    is_active = Column(Boolean, default=True)


# Modelo de Cliente (quien envía el paquete)
class Client(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    bank = Column(String, nullable=False)
    account_type = Column(Enum(AccountType, name="tipo_cuenta"), default=AccountType.AHORRO)
    is_active = Column(Boolean, default=True)

    deliveries = relationship("Delivery", back_populates="client")


# Modelo de Domicilio (el paquete en tránsito)
class Delivery(Base):
    __tablename__ = 'deliveries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False, index=True)
    rider_id = Column(Integer, ForeignKey('riders.id'), nullable=True, index=True)  # Puede ser NULL hasta que se asigne
    package_name = Column(String, nullable= False)

    receptor_name = Column(String, nullable = False)
    receptor_number = Column(Integer, nullable = False)

    delivery_address = Column(String, nullable=False)
    state = Column(Enum(DeliveryStanding, name="delivery_state"), default=DeliveryStanding.PENDING )

    delivery_total_amount = Column(Float, nullable= False, default=0.0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    delivery_date = Column(DateTime, nullable=True)

    client = relationship("Client", back_populates="deliveries")
    rider = relationship("Rider", back_populates="deliveries")
    payments = relationship("Payment", back_populates="delivery")


# Modelo de Domiciliario (quien entrega el paquete)
class Rider(Base):
    __tablename__ = 'riders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    plate = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    deliveries = relationship("Delivery", back_populates="rider")



#  Modelo de Pago
class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_id = Column(Integer, ForeignKey('deliveries.id'))
    settlement_status = Column(Enum(SettlementStatus, name = "settlement_status"), default = SettlementStatus.PENDING)
    payment_type = Column(Enum(PaymentType, name = "Type_of_payment"), default = PaymentType.CASH)
    payment_status = Column(Enum(PaymentStatus, name = "Status_of_payment"), default = PaymentStatus.COURIER)
    payment_reference = Column(String(255), nullable=True)
    total_amount = Column(Float, nullable=False)  # 12,000 por domicilio
    rider_amount = Column(Float, nullable=False)  # 10,000 para el domiciliario
    coop_amount = Column(Float, nullable=False)  # 2,000 para la cooperativa
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    delivery = relationship("Delivery", back_populates="payments")


