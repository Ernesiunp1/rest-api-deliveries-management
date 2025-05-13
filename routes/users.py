from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth.auth import hash_password, verify_password, create_access_token, auth_user
from db.db import get_db, db_dependency
from models.models import User
from schemas.schemas import UserCreate, UserResponse, UserToUpdate, UserUpdated, UserRole
from fastapi.security import OAuth2PasswordRequestForm

user_route = APIRouter(prefix="/user", tags=["Users"])


# Ruta para crear un usuario
@user_route.post("/register", response_model=UserResponse)
def register(user: UserCreate, db = db_dependency):

    db_user = db.query(User).filter(or_(User.username == user.username.lower(), User.email == user.email)).first()

    if db_user:
        raise HTTPException(status_code=400, detail="username or password already exist")


    new_user = User(username=user.username.strip().lower(),
                    hashed_password=hash_password(user.password),
                    email = user.email.strip().lower())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# Ruta para obtener todos los usuarios
@user_route.get("/users/")
def get_users(db = db_dependency):
# def get_users(db = db_dependency, user = Depends(auth_user)):
    return db.query(User).all()


@user_route.put("/update_user")
async def update_user(user_id, user_to_update: UserToUpdate,
                      db = db_dependency, auth = Depends(auth_user)):

    is_user = db.query(User).filter(User.id == user_id).first()

    if not is_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="user not found in db")

    db_user = is_user

    if user_to_update.username:
        db_user.username = user_to_update.username.lower()
    if user_to_update.email:
        db_user.email = user_to_update.email.lower()

    db.commit()
    db.refresh(db_user)

    return db_user



@user_route.put("/new_password")
async def update_password(new_password, old_password,
                          db = db_dependency, auth= Depends(auth_user)):

    user_identity = db.query(User).filter(User.username == auth.username).first()

    print(user_identity)

    user_db = db.query(User).filter(User.id == user_identity.id).first()
    if not user_db:
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail=f"user with id do not exist")

    checking_pass = verify_password(old_password, user_db.hashed_password)
    if not checking_pass:
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED,
                            detail = f"user o password invalid")

    if checking_pass:
        new_hashed_password = hash_password(new_password)
        user_db.hashed_password = new_hashed_password

        db.commit()
        db.refresh(user_db)

        return user_db


@user_route.delete("/delete_user")
async def delete_user(id_to_delete, auth = Depends(auth_user), db = db_dependency):

    identity_user = db.query(User).filter(User.username == auth.username).first()
    if not identity_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDEN, YOU MUST BE ADMIN")

    user_to_deactive = db.query(User).filter(User.id == id_to_delete).first()

    if not user_to_deactive:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"user with id {id_to_delete}, not found")

    else:
        user_to_deactive.is_active = False
        db.commit()

        return {
            "status": status.HTTP_200_OK,
            "msg": "User was deleted"
        }

