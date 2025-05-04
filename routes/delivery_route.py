import math
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import desc

from db.db import db_dependency
from models.models import Delivery, Rider, Payment, Client
from schemas.schemas import CreatePackage, PackageResponse, DeliveryStanding, DeliveryUpdate, DeliveryUpdateRespose, \
    PaymentCreate, PaymentType, PaymentStatus, SettlementStatus
from sqlalchemy.orm import joinedload
import datetime

from datetime import datetime, timedelta

dely_route = APIRouter(prefix="/deliveries", tags=["Deliveries"])





@dely_route.get("/")
async def get_all_deliveries(
        page: int = 1,
        size: int = 20,
        state: DeliveryStanding = None,
        db=db_dependency
):
    query = db.query(Delivery).options(
        joinedload(Delivery.rider),
        joinedload(Delivery.client),
        joinedload(Delivery.payments)
    )

    if state:
        query = query.filter(Delivery.state == state)

    # Ordenar por fecha de creación descendente
    query = query.order_by(desc(Delivery.created_at))

    # Contar total antes de paginar
    total = query.count()

    # Aplicar paginación
    query = query.offset((page - 1) * size).limit(size)

    deliveries = query.all()



    return {
        "items": deliveries,
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size)
    }


@dely_route.get("/filtered")
async def get_filtered_deliveries(
        time_period: str = Query(..., description="Periodo de tiempo: 'today', 'week', 'month', 'custom'"),
        start_date: Optional[datetime] = Query(None, description="Fecha de inicio para filtro personalizado"),
        end_date: Optional[datetime] = Query(None, description="Fecha de fin para filtro personalizado"),
        page: int = 1,
        size: int = 20,
        state: DeliveryStanding = None,
        db=db_dependency
):
    # Iniciamos la query con los joins necesarios
    query = db.query(Delivery).options(
        joinedload(Delivery.rider),
        joinedload(Delivery.client),
        joinedload(Delivery.payments)
    )

    # Aplicamos filtro de estado si existe
    if state:
        query = query.filter(Delivery.state == state)

    # Obtenemos la fecha y hora actual
    current_datetime = datetime.now()

    # Aplicamos filtros según el periodo seleccionado
    if time_period == "today":
        # Filtro para el día actual (desde las 00:00:00 hasta ahora)
        today_start = datetime(current_datetime.year, current_datetime.month, current_datetime.day)
        query = query.filter(Delivery.created_at >= today_start)

    elif time_period == "week":
        # Filtro para la semana actual (desde el lunes hasta ahora)
        days_since_monday = current_datetime.weekday()  # 0 para lunes, 6 para domingo
        week_start = current_datetime - timedelta(days=days_since_monday)
        week_start = datetime(week_start.year, week_start.month, week_start.day)
        query = query.filter(Delivery.created_at >= week_start)

    elif time_period == "month":
        # Filtro para el mes actual (desde el día 1 hasta ahora)
        month_start = datetime(current_datetime.year, current_datetime.month, 1)
        query = query.filter(Delivery.created_at >= month_start)

    elif time_period == "custom" and start_date:
        # Filtro personalizado con fechas específicas
        query = query.filter(Delivery.created_at >= start_date)
        if end_date:
            # Si hay fecha de fin, incluimos hasta ese día a las 23:59:59
            end_of_day = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
            query = query.filter(Delivery.created_at <= end_of_day)

    # Ordenar por fecha de creación descendente
    query = query.order_by(desc(Delivery.created_at))

    # Contar total de resultados con los filtros aplicados
    total = query.count()

    # Aplicar paginación
    query = query.offset((page - 1) * size).limit(size)

    deliveries = query.all()

    return {
        "items": deliveries,
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size),
        "filter": {
            "time_period": time_period,
            "start_date": start_date,
            "end_date": end_date
        }
    }




@dely_route.post("/new_delivery", response_model=PackageResponse)
def new_delivery( package: CreatePackage, client, rider = 0, total_amount = 10000,  db = db_dependency):

    if rider == "null":
        rider = None

    new_package = {
        "client_id": client,
        "rider_id": rider,
        "package_name": package.package_name,
        "receptor_name": package.receptor_name,
        "receptor_number": package.receptor_number,
        "delivery_total_amount": package.delivery_total_amount,
        "delivery_address": f"{package.delivery_address} ({package.delivery_location.value})",
        "state": package.state,
        "created_at": package.created_at,
        "delivery_date": package.delivery_date
    }

    package_to_save = Delivery(** new_package)

    db.add(package_to_save)
    db.flush()

    rider_amount = (float(total_amount) * 0.8)
    coop_amount = (float(total_amount) * 0.2)

    print(rider_amount, type(rider_amount))
    print(coop_amount, type(coop_amount))

    payment_data = {
        "delivery_id": package_to_save.id,
        "total_amount": total_amount,
        "rider_amount": rider_amount,
        "coop_amount": coop_amount,
        "payment_type": PaymentType.CASH,
        "payment_status": PaymentStatus.COURIER,
        "settlement_status": SettlementStatus.PENDING,
        "payment_reference": None,
        "created_at": datetime.utcnow()

    }

    new_payment: PaymentCreate = Payment(**payment_data)

    db.add(new_payment)



    db.commit()
    db.refresh(package_to_save)

    return package_to_save

@dely_route.get("/get_deliveries_by_status")
async def get_deliveries_by_status(delivery_status: DeliveryStanding, db = db_dependency ):

    deliveries = [delivery for delivery in db.query(Delivery).all() if delivery.state == delivery_status]

    for delivery in deliveries:
        client = db.query(Client).filter(Client.id == delivery.client_id).first()

        cliente = delivery.client



    if not deliveries:
        raise HTTPException(status_code=status.HTTP_200_OK,
                            detail=f"There is not deliveries for this status: {delivery_status}")

    return deliveries


@dely_route.get("/client")
async def get_deliveries_by_client(client_id, db=db_dependency):

    deliveries = (db.query(Delivery).options(joinedload(Delivery.payments))
                  .filter(Delivery.client_id == client_id).all())

    return deliveries


@dely_route.put("/add_rider")
async def add_rider_to_delivery(rider_id, delivery_id, db = db_dependency):

    check_rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not check_rider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Rider with id {rider_id} not found")

    delivery = db.query(Delivery).filter(Delivery.id == delivery_id).first()

    delivery.state = DeliveryStanding.ASSIGNED

    if not delivery.rider_id:
        delivery.rider_id = rider_id



        db.commit()
        db.refresh(delivery)

        return delivery

    else:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"The delivery already has a rider")



@dely_route.put("/update", response_model=DeliveryUpdateRespose)
async def update_delivery( delivery_id, delivery: DeliveryUpdate, db = db_dependency,):

    delivery_db = db.query(Delivery).filter(Delivery.id == delivery_id).first()

    if not delivery_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"delivery with id {delivery_id} not found")

    if delivery.delivery_address:
        delivery_db.delivery_address = delivery.delivery_address
    if delivery.delivery_date:
        delivery_db.delivery_date = delivery.delivery_date
    if delivery.state:
        delivery_db.state = delivery.state
    if delivery.package_name:
        delivery_db.package_name = delivery.package_name

    db.commit()
    db.refresh(delivery_db)

    return delivery_db


@dely_route.get("/states")
async def get_delivery_states():
    return [state.value for state in DeliveryStanding]

