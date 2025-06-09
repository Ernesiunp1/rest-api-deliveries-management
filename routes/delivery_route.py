import math
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query, Response
from sqlalchemy import desc

from db.db import db_dependency
from models.models import Delivery, Rider, Payment, Client
from schemas.schemas import CreatePackage, PackageResponse, DeliveryStanding, DeliveryUpdate, DeliveryUpdateRespose, \
    PaymentCreate, PaymentType, PaymentStatus, SettlementStatus, Etiqueta
from sqlalchemy.orm import joinedload
import datetime
from utils.mapping import get_delivery_fee

from datetime import datetime, timedelta

from reportlab.lib.pagesizes import A6, letter
from reportlab.pdfgen import canvas
from io import BytesIO

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
def new_delivery( package: CreatePackage, client, rider = 0,
                  total_amount = 10000, coop_amount = 2000, db = db_dependency):

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
        "delivery_comment": package.delivery_comment,
        "state": package.state,
        "created_at": package.created_at,
        "delivery_date": package.delivery_date
    }

    package_to_save = Delivery(** new_package)


    db.add(package_to_save)
    db.flush()

    monto_domicilio = package.monto_domicilio

    total_amount = float(total_amount)
    coop_amount = float(coop_amount)
    rider_amount = monto_domicilio - coop_amount

    client_amount = total_amount - monto_domicilio

    print("tipo del rider_amount", rider_amount, type(rider_amount))
    print("tipo del coop amount", coop_amount, type(coop_amount))
    print("tota del coop amount", coop_amount, type(coop_amount))

    payment_data = {
        "delivery_id": package_to_save.id,
        "total_amount": total_amount,
        "rider_amount": rider_amount,
        "coop_amount": coop_amount,
        "payment_type": PaymentType.PENDING,
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




@dely_route.post("/generate-label/")
def generate_label(domicilio: dict, db=db_dependency):


    query = db.query(Delivery).options(
        joinedload(Delivery.rider),
        joinedload(Delivery.client),
        joinedload(Delivery.payments)
    )

    domi = query.filter(Delivery.id == domicilio['id']).first()

    print("domicilio", domi)

    client_name = domi.client.client_name if domi.client else "Desconocido"
    rider_name = domi.rider.name if domi.rider else "Sin asignar"
    fecha_creacion = domi.created_at

    print("client_name", client_name)
    print("rider_name", rider_name)
    print("fecha_creacion", fecha_creacion)

    half_letter = (letter[0], letter[1] / 2)  # (612, 396)
    altura_hoja = half_letter[1]

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=half_letter)
    p.setFont("Helvetica", 14)


    p.drawString(30, 350, f"ID: {domicilio['id']}")
    p.drawString(30, 330, f"Rider: {rider_name}")
    p.drawString(30, 310, f"Cliente: {client_name}")
    p.drawString(30, 290, f"Nombre Paquete: {domicilio['package_name']}")
    p.drawString(30, 270, f"Dirección: {domicilio['delivery_address']} ")
    p.drawString(30, 250, f"Barrio: {domicilio['delivery_location']}")
    p.drawString(30, 230, f"Receptor: {domicilio['receptor_name']} ")
    p.drawString(30, 210, f"Número Receptor: {domicilio['receptor_number']} ")
    p.drawString(30, 190, f"Fecha creación: {fecha_creacion}")
    p.drawString(30, 170, f"Comentario: {domicilio['delivery_comment']}")
    p.drawString(30, 150, f"Monto a cobrar: {domicilio['delivery_total_amount']}")
    p.showPage()
    p.save()

    buffer.seek(0)
    return Response(content=buffer.getvalue(), media_type="application/pdf")



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

