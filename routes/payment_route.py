# payment_routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from sqlalchemy.orm import joinedload
from typing import List, Optional

from db.db import db_dependency
from datetime import datetime, timedelta
from models.models import Payment, Delivery, Rider, Client
from schemas.schemas import PaymentStatus, SettlementStatus, PaymentType
from pydantic import BaseModel, Field

payment_route = APIRouter(prefix="/payments", tags=["Payments"])


# Esquemas de respuesta
class DashboardSummary(BaseModel):
    pendingRiderPayments: int
    pendingRiderAmount: float
    pendingClientPayments: int
    pendingClientAmount: float
    totalTransactions: int
    totalAmount: float


class PaymentDetail(BaseModel):
    id: int
    delivery_id: int
    settlement_status: str
    payment_type: str
    payment_status: str
    payment_reference: Optional[str] = None
    total_amount: float
    rider_amount: float
    coop_amount: float
    comments: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    delivery_id: int
    payment_type: str
    payment_status: str
    payment_reference: Optional[str] = None
    total_amount: float
    rider_amount: float
    coop_amount: float
    comments: Optional[str] = None


class PaymentUpdate(BaseModel):
    settlement_status: Optional[str] = None
    payment_status: Optional[str] = None
    payment_reference: Optional[str] = None
    comments: Optional[str] = None


# Dashboard endpoint
@payment_route.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(db=db_dependency):
    # Consulta para pagos pendientes de domiciliarios
    rider_payments_query = db.query(
        func.count(Payment.id).label("count"),
        func.sum(Payment.rider_amount).label("total")
    ).join(Delivery, Payment.delivery_id == Delivery.id) \
        .filter(Payment.settlement_status == SettlementStatus.PENDING) \
        .filter(Payment.payment_status == PaymentStatus.COURIER)

    rider_result = rider_payments_query.first()

    # Consulta para pagos pendientes de clientes
    client_payments_query = db.query(
        func.count(Payment.id).label("count"),
        func.sum(Payment.total_amount).label("total")
    ).join(Delivery, Payment.delivery_id == Delivery.id) \
        .filter(Payment.payment_status == PaymentStatus.CLIENT)

    client_result = client_payments_query.first()

    # Total de transacciones y montos
    total_query = db.query(
        func.count(Payment.id).label("count"),
        func.sum(Payment.total_amount).label("total")
    )

    total_result = total_query.first()

    return {
        "pendingRiderPayments": rider_result.count or 0 if rider_result else 0,
        "pendingRiderAmount": float(rider_result.total or 0) if rider_result and rider_result.total else 0,
        "pendingClientPayments": client_result.count or 0 if client_result else 0,
        "pendingClientAmount": float(client_result.total or 0) if client_result and client_result.total else 0,
        "totalTransactions": total_result.count or 0 if total_result else 0,
        "totalAmount": float(total_result.total or 0) if total_result and total_result.total else 0
    }


# Endpoints para gestión de pagos de domiciliarios
@payment_route.get("/riders-payments", response_model=List[dict])
async def get_riders_payments(
        settlement_status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db=db_dependency
):
    # Consulta base
    query = db.query(
        Rider.id.label("rider_id"),
        Rider.name.label("rider_name"),
        Rider.phone.label("rider_phone"),
        func.count(Payment.id).label("total_deliveries"),
        func.sum(Payment.rider_amount).label("total_amount"),
        func.sum(case((Payment.settlement_status == SettlementStatus.PENDING, Payment.rider_amount), else_=0)).label(
            "pending_amount")
    ).join(Delivery, Delivery.rider_id == Rider.id) \
        .join(Payment, Payment.delivery_id == Delivery.id) \
        .filter(Payment.payment_status == PaymentStatus.COURIER)

    # Aplicar filtros opcionales
    if settlement_status:
        query = query.filter(Payment.settlement_status == settlement_status)

    if start_date:
        query = query.filter(Payment.created_at >= start_date)

    if end_date:
        query = query.filter(Payment.created_at <= end_date)

    # Agrupar por domiciliario
    query = query.group_by(Rider.id, Rider.name, Rider.phone)

    # Ordenar por monto pendiente de mayor a menor
    query = query.order_by(desc("pending_amount"))

    results = query.all()

    return [
        {
            "rider_id": result.rider_id,
            "rider_name": result.rider_name,
            "rider_phone": result.rider_phone,
            "total_deliveries": result.total_deliveries,
            "total_amount": float(result.total_amount) if result.total_amount else 0,
            "pending_amount": float(result.pending_amount) if result.pending_amount else 0
        }
        for result in results
    ]


@payment_route.get("/riders-payments/{rider_id}", response_model=List[dict])
async def get_rider_payment_details(
        rider_id: int,
        settlement_status: Optional[str] = None,
        db=db_dependency
):
    # Consulta para obtener detalles de pagos por domiciliario
    query = db.query(
        Payment.id.label("payment_id"),
        Delivery.id.label("delivery_id"),
        Payment.created_at.label("date"),
        Payment.total_amount.label("total_amount"),
        Payment.rider_amount.label("rider_amount"),
        Payment.settlement_status.label("settlement_status"),
        Payment.payment_type.label("payment_type")
    ).join(Delivery, Payment.delivery_id == Delivery.id) \
        .filter(Delivery.rider_id == rider_id)

    if settlement_status:
        query = query.filter(Payment.settlement_status == settlement_status)

    # Ordenar por fecha de creación (más reciente primero)
    query = query.order_by(desc(Payment.created_at))

    results = query.all()

    return [
        {
            "payment_id": result.payment_id,
            "delivery_id": result.delivery_id,
            "date": result.date,
            "total_amount": float(result.total_amount),
            "rider_amount": float(result.rider_amount),
            "settlement_status": result.settlement_status.value,
            "payment_type": result.payment_type.value
        }
        for result in results
    ]


# @payment_route.post("/riders-payments/{rider_id}/settle")
# async def settle_rider_payments(
#         rider_id: int,
#         payment_ids: List[int],
#         comments: Optional[str] = None,
#         db=db_dependency
# ):
#
#     print(rider_id, payment_ids, comments)
#     # Verificar que los pagos existan y correspondan al domiciliario
#     payments = db.query(Payment).join(Delivery).filter(
#         Payment.id.in_(payment_ids),
#         Delivery.rider_id == rider_id
#     ).all()
#
#     if len(payments) != len(payment_ids):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Algunos pagos no existen o no corresponden al domiciliario especificado"
#         )
#
#     # Actualizar estado de los pagos a liquidado
#     for payment in payments:
#         payment.settlement_status = SettlementStatus.SETTLED
#         payment.comments = comments
#         payment.updated_at = datetime.utcnow()
#
#     db.commit()
#
#     return {"message": f"Se han liquidado {len(payments)} pagos"}


class SettlePaymentsRequest(BaseModel):
    payment_ids: List[int]
    comments: Optional[str] = None

@payment_route.post("/riders-payments/{rider_id}/settle")
async def settle_rider_payments(
    rider_id: int,
    body: SettlePaymentsRequest,
    db=db_dependency
):
    if not body.payment_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere al menos un ID de pago para liquidar"
        )

    print(rider_id, body.payment_ids, body.comments)

    # Buscar los pagos que coincidan con los IDs y el rider
    payments = db.query(Payment).join(Delivery).filter(
        Payment.id.in_(body.payment_ids),
        Delivery.rider_id == rider_id
    ).all()

    if len(payments) != len(body.payment_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Algunos pagos no existen o no corresponden al domiciliario especificado"
        )

    # Actualizar estado de cada pago
    for payment in payments:
        payment.settlement_status = SettlementStatus.SETTLED
        payment.comments = body.comments
        payment.updated_at = datetime.utcnow()

    db.commit()

    return {"message": f"Se han liquidado {len(payments)} pagos"}


# Endpoints para gestión de pagos de clientes
@payment_route.get("/clients-payments", response_model=List[dict])
async def get_clients_payments(
        payment_status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db=db_dependency
):
    # Consulta base
    query = db.query(
        Client.id.label("client_id"),
        Client.client_name.label("client_name"),
        Client.phone.label("client_phone"),
        func.count(Payment.id).label("total_deliveries"),
        func.sum(Payment.total_amount).label("total_amount"),
        func.sum(case((Payment.payment_status == PaymentStatus.CLIENT, Payment.total_amount), else_=0)).label(
            "pending_amount")
    ).join(Delivery, Delivery.client_id == Client.id) \
        .join(Payment, Payment.delivery_id == Delivery.id)

    # Aplicar filtros opcionales
    if payment_status:
        query = query.filter(Payment.payment_status == payment_status)

    if start_date:
        query = query.filter(Payment.created_at >= start_date)

    if end_date:
        query = query.filter(Payment.created_at <= end_date)

    # Agrupar por cliente
    query = query.group_by(Client.id, Client.client_name, Client.phone)

    # Ordenar por monto pendiente de mayor a menor
    query = query.order_by(desc("pending_amount"))

    results = query.all()

    return [
        {
            "client_id": result.client_id,
            "client_name": result.client_name,
            "client_phone": result.client_phone,
            "total_deliveries": result.total_deliveries,
            "total_amount": float(result.total_amount) if result.total_amount else 0,
            "pending_amount": float(result.pending_amount) if result.pending_amount else 0
        }
        for result in results
    ]


@payment_route.get("/clients-payments/{client_id}", response_model=List[dict])
async def get_client_payment_details(
        client_id: int,
        payment_status: Optional[str] = None,
        db=db_dependency
):
    # Consulta para obtener detalles de pagos por cliente
    query = db.query(
        Payment.id.label("payment_id"),
        Delivery.id.label("delivery_id"),
        Payment.created_at.label("date"),
        Payment.total_amount.label("total_amount"),
        Payment.payment_status.label("payment_status"),
        Payment.payment_type.label("payment_type")
    ).join(Delivery, Payment.delivery_id == Delivery.id) \
        .filter(Delivery.client_id == client_id)

    if payment_status:
        query = query.filter(Payment.payment_status == payment_status)

    # Ordenar por fecha de creación (más reciente primero)
    query = query.order_by(desc(Payment.created_at))

    results = query.all()

    return [
        {
            "payment_id": result.payment_id,
            "delivery_id": result.delivery_id,
            "date": result.date,
            "total_amount": float(result.total_amount),
            "payment_status": result.payment_status.value,
            "payment_type": result.payment_type.value
        }
        for result in results
    ]


@payment_route.post("/clients-payments/{client_id}/receive")
async def receive_client_payments(
        client_id: int,
        payment_ids: List[int],
        payment_type: str,
        payment_reference: Optional[str] = None,
        comments: Optional[str] = None,
        db=db_dependency
):
    # Verificar que los pagos existan y correspondan al cliente
    payments = db.query(Payment).join(Delivery).filter(
        Payment.id.in_(payment_ids),
        Delivery.client_id == client_id
    ).all()

    if len(payments) != len(payment_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Algunos pagos no existen o no corresponden al cliente especificado"
        )

    # Actualizar estado de los pagos a recibido
    for payment in payments:
        payment.payment_status = PaymentStatus.RECEIVED
        payment.payment_type = PaymentType(payment_type)
        payment.payment_reference = payment_reference
        payment.comments = comments
        payment.updated_at = datetime.utcnow()

    db.commit()

    return {"message": f"Se han registrado {len(payments)} pagos recibidos"}


# Endpoint para el resumen general de pagos
@payment_route.get("/summary", response_model=dict)
async def get_payment_summary(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db=db_dependency
):
    # Si no se especifican fechas, usar el mes actual
    if not start_date:
        start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if not end_date:
        # Último día del mes actual
        next_month = start_date.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)
        end_date = end_date.replace(hour=23, minute=59, second=59)

    # Estadísticas de pagos
    total_query = db.query(
        func.count(Payment.id).label("total_count"),
        func.sum(Payment.total_amount).label("total_amount"),
        func.sum(Payment.rider_amount).label("rider_amount"),
        func.sum(Payment.coop_amount).label("coop_amount")
    ).filter(Payment.created_at.between(start_date, end_date))

    total_result = total_query.first()

    # Pagos por estado
    status_query = db.query(
        Payment.payment_status,
        func.count(Payment.id).label("count"),
        func.sum(Payment.total_amount).label("amount")
    ).filter(Payment.created_at.between(start_date, end_date)) \
        .group_by(Payment.payment_status)

    status_results = status_query.all()

    status_summary = {
        status_.value: {
            "count": count,
            "amount": float(amount) if amount else 0
        }
        for status_, count, amount in status_results
    }

    # Pagos por tipo
    type_query = db.query(
        Payment.payment_type,
        func.count(Payment.id).label("count"),
        func.sum(Payment.total_amount).label("amount")
    ).filter(Payment.created_at.between(start_date, end_date)) \
        .group_by(Payment.payment_type)

    type_results = type_query.all()

    type_summary = {
        payment_type.value: {
            "count": count,
            "amount": float(amount) if amount else 0
        }
        for payment_type, count, amount in type_results
    }

    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "totals": {
            "count": total_result.total_count or 0,
            "total_amount": float(total_result.total_amount or 0),
            "rider_amount": float(total_result.rider_amount or 0),
            "coop_amount": float(total_result.coop_amount or 0)
        },
        "by_status": status_summary,
        "by_type": type_summary
    }






@payment_route.post("/", response_model=PaymentDetail)
async def create_payment(payment: PaymentCreate, db=db_dependency):
    # Verificar que el domicilio existe
    delivery = db.query(Delivery).filter(Delivery.id == payment.delivery_id).first()
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domicilio no encontrado"
        )

    new_payment = Payment(
        delivery_id=payment.delivery_id,
        payment_type=PaymentType(payment.payment_type),
        payment_status=PaymentStatus(payment.payment_status),
        payment_reference=payment.payment_reference,
        total_amount=payment.total_amount,
        rider_amount=payment.rider_amount,
        coop_amount=payment.coop_amount,
        comments=payment.comments
    )

    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    return new_payment


@payment_route.get("/{payment_id}", response_model=PaymentDetail)
async def get_payment(payment_id: int, db=db_dependency):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )

    return payment


@payment_route.patch("/{payment_id}", response_model=PaymentDetail)
async def update_payment(payment_id: int, data: PaymentUpdate, db=db_dependency):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )

    # Actualizar campos si se proporcionan
    if data.settlement_status:
        payment.settlement_status = SettlementStatus(data.settlement_status)

    if data.payment_status:
        payment.payment_status = PaymentStatus(data.payment_status)

    if data.payment_reference is not None:
        payment.payment_reference = data.payment_reference

    if data.comments is not None:
        payment.comments = data.comments

    payment.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(payment)

    return payment


@payment_route.delete("/{payment_id}")
async def delete_payment(payment_id: int, db=db_dependency):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )

    db.delete(payment)
    db.commit()

    return {"message": "Pago eliminado correctamente"}