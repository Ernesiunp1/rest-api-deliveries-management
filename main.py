from fastapi import FastAPI
from db.db import Base, engine
from routes.auth import auth_route
from routes.users import user_route
from routes.client_route import client_route
from routes.delivery_route import dely_route
from routes.riders_route import rider_route
from routes.payment_route import payment_route
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

Base.metadata.create_all(bind=engine)
routers = [user_route, rider_route,
           dely_route, client_route,
           auth_route, payment_route]




app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8100"],  # O mejor: ["http://localhost:4200"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



for router in routers:
    app.include_router(router)

