from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import joinedload

from auth.auth import auth_user
from db.db import db_dependency
from models.models import Client, User
from schemas.schemas import CreateClient, ClientResponse, ClientUpdate, UserRole

client_route = APIRouter(prefix="/client", tags= ["Clients"])


@client_route.post("/create_client", response_model= ClientResponse)
async def new_client( client: CreateClient, db = db_dependency):

    is_client = db.query(Client).filter(Client.phone == client.phone).first()
    if is_client:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user already exist")

    client = client.dict()

    client_data = {
        "client_name": client.get("client_name").lower(),
        "phone": client["phone"].lower(),
        "address": client["address"].lower(),
        "bank": client.get("bank").lower(),
        "account_type": client.get("account_type"),
        "account_number": client.get("account_number")
    }

    client_payload = Client(**client_data)

    db.add(client_payload)
    db.commit()
    db.refresh(client_payload)

    return client_payload


@client_route.get("/get_all")
async def get_all_clients(db= db_dependency):
    clients = db.query(Client).all()
    if not clients:
        return HTTPException(status_code=status.HTTP_200_OK, detail="there's no clients registred yet")

    return clients


@client_route.get("/by_name")
async def get_user_by_name(name: str, db = db_dependency):

    normal_name = name.lower().strip()

    client = (
        db.query(Client)
        .options(joinedload(Client.deliveries))  # Precarga los deliveries
        .filter(Client.client_name == normal_name)
        .first()
    )

    if not client:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

    return client


@client_route.put("/update")
async def update_client(client: ClientUpdate, client_id: int, db = db_dependency, identity = Depends(auth_user)):
    user_identity: User = db.query(User).filter(User.username == identity.username).first()

    if not user_identity.role == UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="UNAUTHORIZE YOU MUST BE ADMIN")

    print("CLIENTE A ACTUALIZAR EN EL SERVIDOR", client)

    client_db = db.query(Client).filter( Client.id == client_id ).first()

    if not client_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"client with {client_id}, not found")

    if client.client_name:
        client_db.client_name = client.client_name
    if client.phone:
        client_db.phone = client.phone
    if client.address:
        client_db.address = client.address
    if client.bank:
        client_db.bank = client.bank
    if client.account_type:
        client_db.account_type = client.account_type
    if client.account_number:
        client_db.account_number = client.account_number

    db.commit()
    db.refresh(client_db)

    return client_db


@client_route.delete("/delete")
async def delete_client( client_id, db = db_dependency, identity = Depends(auth_user) ):

    user_identity = db.query(User).filter(User.username == identity.username).first()
    if not user_identity:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="you must be ADMIN")


    client_db = db.query(Client).filter(Client.id == client_id).first()

    if not client_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"client with id {client_id}, not found")

    client_db.is_active = False

    db.commit()
    db.refresh(client_db)

    return client_db