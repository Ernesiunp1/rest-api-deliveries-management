from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth.auth import hash_password, verify_password, create_access_token, auth_user
from db.db import get_db, db_dependency
from models.models import User
from schemas.schemas import UserCreate, UserResponse, UserToUpdate, UserUpdated, UserRole
from fastapi.security import OAuth2PasswordRequestForm

auth_route = APIRouter(tags=["Auth"])


@auth_route.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
