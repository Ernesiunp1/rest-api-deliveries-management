import math
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from auth.auth import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM, auth_user
from db.db import db_dependency
from models.models import User, Rider, Payment, Delivery
from schemas.schemas import BikerCreate, BikerResponse, RiderResponseList, RiderSchema, DeliveryStanding, \
    SettlementStatus
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth.auth import oauth2_scheme
from jose import JWTError, jwt

rider_route = APIRouter(prefix="/rider", tags=["Riders"])


@rider_route.get("/")
async def get_all_riders(
        page: int = 1,
        size: int = 20,
        is_active: bool = True,
        db=db_dependency):
    # Primero obtener el conteo
    query = db.query(Rider)

    if is_active:
        query = query.filter(Rider.is_active)

    # Contar el total antes de aplicar limit/offset
    total = query.count()

    # Aplicar paginación
    riders = query.offset((page - 1) * size).limit(size).all()

    if not riders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NO HAY USUARIOS DISPONIBLES"
        )

    return {"total": total, "riders": riders}


# @rider_route.get("/")
# async def get_all_riders(
#         page: int = 1,
#         size: int = 20,
#         is_active: bool = True,
#         db=db_dependency
# ):
#     query = db.query(Rider).options(
#         joinedload(Rider.deliveries).joinedload(Delivery.payments)
#
#
#     )
#
#     if is_active:
#         query = query.filter(Rider.is_active)
#
#     # Ordenar por fecha de creación descendente
#     # query = query.order_by(desc(Delivery.created_at))
#
#     # Contar total antes de paginar
#     total = query.count()
#
#     # Aplicar paginación
#     query = query.offset((page - 1) * size).limit(size)
#
#     riders = query.all()
#
#
#
#     return {
#         "items": riders,
#         "total": total,
#         "page": page,
#         "size": size,
#         "pages": math.ceil(total / size)
#     }






@rider_route.post("/newbiker")
def new_biker(rider: BikerCreate, db = db_dependency,  user = Depends(auth_user)):
    rider_db = db.query(Rider).filter(Rider.name == rider.name).first()
    if rider_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=" Rider ya existe")

    new_rider = Rider(name = rider.name, phone = rider.phone, plate = rider.plate)

    db.add(new_rider)
    db.commit()
    db.refresh(new_rider)
    return new_rider


@rider_route.get("/get_riders")
async def get_all_bikers(db=db_dependency):
    riders = db.query(Rider).all()

    if not riders:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"theres no riders yet, riders not found")

    return riders


@rider_route.get("/get_by_delivery_id")
async def get_rider_by_id(delivery_id, db =db_dependency):
    delivery = db.query(Delivery).options( joinedload(Delivery.rider) ).filter(Delivery.id == delivery_id).first()

    rider_name = delivery.rider.name


    return rider_name

@rider_route.get("/by_name")
async def get_rider_by_name(name: str, db=db_dependency):
    normal_name = name.lower().strip()

    rider = (
        db.query(Rider)
        .filter(Rider.name == normal_name)
        .first()
    )

    if not rider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rider with name {name} not found")

    return rider



@rider_route.get("/actions")
async def get_actions(db=db_dependency):
    riders = (
        db.query(Rider)
        .options(
            joinedload(Rider.deliveries).joinedload(Delivery.payments)  # Precarga Deliveries y Payments
        )
        .all()
    )

    if not riders:
        raise HTTPException(status_code=404, detail="No riders found")

    return riders


@rider_route.get("/{rider_id}")
async def get_rider_details(rider_id: int, db=db_dependency):
    # Obtener información básica del domiciliario
    rider = db.query(Rider).filter(Rider.id == rider_id).first()

    if not rider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domiciliario no encontrado"
        )

    # Obtener los domicilios con sus pagos asociados
    deliveries = db.query(Delivery).options(
        joinedload(Delivery.payments)
    ).filter(Delivery.rider_id == rider_id).all()

    # Calcular estadísticas
    total_deliveries = len(deliveries)
    pending_deliveries = sum(1 for d in deliveries if d.state == DeliveryStanding.PENDING)
    in_progress_deliveries = sum(1 for d in deliveries if d.state == DeliveryStanding.IN_PROGRESS)
    completed_deliveries = sum(1 for d in deliveries if d.state == DeliveryStanding.DELIVERED)

    # Calcular ganancias totales
    total_earnings = 0
    pending_payments = 0
    for delivery in deliveries:
        for payment in delivery.payments:
            total_earnings += payment.rider_amount
            if payment.settlement_status == SettlementStatus.PENDING:
                pending_payments += payment.rider_amount

    # Organizar datos para respuesta
    result = {
        "rider_info": {
            "id": rider.id,
            "name": rider.name,
            "phone": rider.phone,
            "plate": rider.plate,
            "is_active": rider.is_active
        },
        "activity_summary": {
            "total_deliveries": total_deliveries,
            "pending_deliveries": pending_deliveries,
            "in_progress_deliveries": in_progress_deliveries,
            "completed_deliveries": completed_deliveries,
            "total_earnings": total_earnings,
            "pending_payments": pending_payments
        },
        "recent_deliveries": [
            {
                "id": delivery.id,
                "created_at": delivery.created_at,
                "delivery_date": delivery.delivery_date,
                "client_name": delivery.client.client_name if delivery.client else None,
                "address": delivery.delivery_address,
                "state": delivery.state.value,
                "total_amount": delivery.delivery_total_amount,
                "payment_info": [
                    {
                        "id": payment.id,
                        "rider_amount": payment.rider_amount,
                        "settlement_status": payment.settlement_status.value,
                        "payment_type": payment.payment_type.value,
                        "payment_status": payment.payment_status.value
                    } for payment in delivery.payments
                ] if delivery.payments else []
            } for delivery in deliveries[:10]  # Mostrar solo los 10 más recientes
        ]
    }

    return result
