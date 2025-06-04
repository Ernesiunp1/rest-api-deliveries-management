from enum import Enum
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


class AccountType(str, Enum):
    AHORRO = "AHORRO"
    CORRIENTE = "CORRIENTE"


class DeliveryStanding(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    CANCELED = "CANCELLED"
    ASSIGNED = "ASSIGNED"


class DeliveryLocations(str, Enum):
    MEDELLIN = 'Medellín',
    BELEN = 'Belen',
    LA_ESTRELLA = 'La Estrella',
    ENVIGADO = 'Envigado',
    ITAGUI = 'Itagui',
    CALDAS = 'Caldas',
    SABANETA = 'Sabaneta',
    SAN_ANTONIO = 'San Antonio de Prado',
    BELLO = 'Bello',
    COPACABANA = 'Copacabana',
    BARBOSA = 'Barbosa',
    GIRARDOTA = 'Girardota',
    SAN_CRISTOBAL = 'San Cristobal',
    MACHADO = 'Machado',




class UserRole(Enum):
    ADMIN = "Admin",
    RIDER = "Rider",
    CLIENT = "Client"


class PaymentType(Enum):
    PENDING = "PENDING"
    CASH = "CASH"
    TRANSFER = "TRANSFER"


class PaymentStatus(Enum):
    # status para conciliar de cara a la empresa

    COURIER = "COURIER"
    OFFICE = "OFFICE"
    OFFICE_RECIEVED_TRANSFER = "OFFICE_RECIEVED_TRANSFER"
    CLIENT_RECIEVED_TRANSFER = "CLIENT_RECEIVED_TRANSFER"
    CLIENT = "CLIENT"



class SettlementStatus(Enum):
    # status para manejar el dinero de cara a la conciliacion con el domiciliario
    PENDING = "PENDING"
    CLEARED = "CLEARED"
    SETTLED = "SETTLED"
    TRANSFER_TO_OFFICE = "TRANSFER_TO_OFFICE"
    TRANFERRED_TO_CLIENT = "TRANSFERRED_TO_CLIENT"




class ClientSettlementStatus(str, Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"


class Etiqueta(BaseModel):
    client_id: int
    rider_id: int
    package_name: str
    receptor_name: str
    receptor_number: int
    delivery_enterprise_amount: float
    delivery_total_amount: float
    delivery_address: str
    delivery_location: str
    delivery_comment: str
    state: str


class TokenData(BaseModel):
    username: str | None = None


class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr


class UserToUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    email: EmailStr | None = None


class UserUpdated(BaseModel):
    username: str | None = None
    password: str | None = None
    email: EmailStr | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True


class BikerCreate(BaseModel):
    name: str
    phone: str
    plate: str


class BikerResponse(BaseModel):
    id: int
    name: str


class RiderResponseList(BaseModel):
    list: BikerResponse


class CreatePackage(BaseModel):
    package_name: str
    receptor_name: str
    receptor_number: int
    delivery_address: str
    delivery_location: DeliveryLocations = DeliveryLocations.MEDELLIN
    state: DeliveryStanding = DeliveryStanding.PENDING
    delivery_total_amount: float
    delivery_comment: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    delivery_date: datetime | None = None


class PackageResponse(BaseModel):
    id: int
    client_id: int
    rider_id: int | None = None
    package_name: str
    delivery_address: str
    state: DeliveryStanding = DeliveryStanding.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    delivery_date: datetime | None = None


class PackageShortRespose(BaseModel):
    client_id: int
    package_name: str
    delivery_address: str
    state: DeliveryStanding = DeliveryStanding.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    delivery_date: datetime | None = None



class CreateClient(BaseModel):
    client_name: str
    phone: str
    address: str
    bank: str
    account_type: AccountType = AccountType.AHORRO
    account_number: int



class ClientResponse(BaseModel):
    client_name: str
    phone: str
    address: str


class ClientUpdate(BaseModel):
    client_name: str | None = None
    phone: str | None = None
    address: str | None = None
    bank: str | None = None
    account_type: AccountType | None = None
    account_number: int | None = None


class ClientUpdateResponse(ClientUpdate):
    pass


class PaymentCreate(BaseModel):
    total_amount: float = Field(10000, gt=0, description="Monto total del pago")
    rider_amount: float = Field(8000, ge=0, description="Monto para el domiciliario")
    coop_amount: float = Field(2000, ge=0, description="Monto para la cooperativa")

    payment_type: PaymentType = PaymentType.CASH
    payment_status: PaymentStatus = PaymentStatus.COURIER
    settlement_status: SettlementStatus = SettlementStatus.PENDING

    payment_reference: Optional[str] = Field(None, max_length=255,
                                             description="Referencia bancaria si es transferencia")

    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    # class Config:
    #    use_enum_values = True Para almacenar los valores de los Enum como strings en la base de datos


class DeliveryUpdate(BaseModel):
    package_name: str | None = None
    delivery_address: str | None = None
    state: DeliveryStanding | None = None
    delivery_date: datetime | None = None


class DeliveryUpdateRespose(DeliveryUpdate):
    pass


class RiderSchema(BaseModel):
    id: int
    name: str
    deliveries: List[PackageResponse]  # Lista de entregas


    class Config:
        from_attributes = True