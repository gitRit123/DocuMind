from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from db.database import get_db
from models.models import User
from core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Check duplicates
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=req.email,
        username=req.username,
        hashed_password=hash_password(req.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, username=user.username)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, username=user.username)


@router.get("/me")
def get_me(db: Session = Depends(get_db)):
    # Protected route example - in real use, inject current_user via dependency
    return {"message": "Use Authorization: Bearer <token> header"}
