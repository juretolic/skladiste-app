from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional, List
from sqlalchemy import func
from app.database import get_db
from app import models, schemas
import redis.asyncio as redis
import json
import pytz
from app.auth import get_current_user

router = APIRouter()

SECRET_KEY = "tajna_lozinka"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Neuspjela autentifikacija",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Korisničko ime već postoji")
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email već postoji")
    hashed_password = get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pogrešan username ili lozinka"
        )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/stock/entry", response_model=schemas.StockEntryResponse)
async def create_stock_entry(entry: schemas.StockEntryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    zagreb = pytz.timezone('Europe/Zagreb')
    now_zagreb = datetime.now(zagreb)
    new_entry = models.StockEntry(
        item_name=entry.item_name,
        quantity=entry.quantity,
        entry_type=entry.entry_type,
        timestamp=now_zagreb,
        user_id=current_user.id
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    # Spremanje eventa u Redis za keširanje
    try:
        redis_client = redis.from_url("redis://redis:6379")
        event_data = {
            "event_type": "stock_entry_created",
            "item_name": entry.item_name,
            "quantity": entry.quantity,
            "entry_type": entry.entry_type,
            "user_id": current_user.id,
            "username": current_user.username,
            "timestamp": now_zagreb.isoformat(),
            "entry_id": new_entry.id
        }
        await redis_client.lpush("recent_events", json.dumps(event_data))
        await redis_client.ltrim("recent_events", 0, 99)  # Zadržavamo samo zadnjih 100 eventova
        await redis_client.close()
    except Exception as e:
        print(f"Greška pri spremanju u Redis: {e}")
    
    # Ponovno dohvatimo unos s korisnikom
    entry_with_user = db.query(models.StockEntry).options(joinedload(models.StockEntry.user)).filter(models.StockEntry.id == new_entry.id).first()
    # Pretvori timestamp u ISO string s time zone info
    entry_with_user.timestamp = entry_with_user.timestamp.astimezone(zagreb).isoformat()
    return entry_with_user

@router.get("/stock/list", response_model=List[schemas.StockEntryResponse])
def list_stock_entries(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    q = db.query(models.StockEntry).options(joinedload(models.StockEntry.user)).order_by(models.StockEntry.timestamp.desc())
    if not current_user.is_admin:
        q = q.filter(models.StockEntry.user_id == current_user.id)
    return q.all()

@router.get("/stock/list/all", response_model=List[schemas.StockEntryResponse])
def list_all_stock_entries_admin(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Ruta za administratora - prikazuje sve unose svih korisnika"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Samo administrator može pristupiti svim unosima")
    return (
        db.query(models.StockEntry)
        .options(joinedload(models.StockEntry.user))
        .order_by(models.StockEntry.timestamp.desc())
        .all()
    )

@router.get("/stock/summary")
def stock_summary(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    entries = (
        db.query(
            models.StockEntry.item_name,
            func.sum(
                func.case(
                    [(models.StockEntry.entry_type == "ulaz", models.StockEntry.quantity)],
                    else_=-models.StockEntry.quantity
                )
            ).label("total_quantity")
        )
        .filter(models.StockEntry.user_id == current_user.id)
        .group_by(models.StockEntry.item_name)
        .all()
    )
    return {item: quantity for item, quantity in entries}

@router.put("/stock/update/{entry_id}", response_model=schemas.StockEntryResponse)
def update_stock_entry(entry_id: int, updated_entry: schemas.StockEntryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    entry = db.query(models.StockEntry).filter(models.StockEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Unos nije pronađen")
    if not (current_user.is_admin or entry.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="Nemate pravo uređivati ovaj unos")
    zagreb = pytz.timezone('Europe/Zagreb')
    entry.item_name = updated_entry.item_name
    entry.quantity = updated_entry.quantity
    entry.entry_type = updated_entry.entry_type
    entry.timestamp = datetime.now(zagreb)
    db.commit()
    db.refresh(entry)
    return entry

@router.delete("/stock/delete/{entry_id}")
async def delete_stock_entry(entry_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    zagreb = pytz.timezone('Europe/Zagreb')
    now_zagreb = datetime.now(zagreb)
    entry = db.query(models.StockEntry).filter(models.StockEntry.id == entry_id, models.StockEntry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Unos nije pronađen")
    
    # Spremanje eventa u Redis prije brisanja
    try:
        redis_client = redis.from_url("redis://redis:6379")
        event_data = {
            "event_type": "stock_entry_deleted",
            "entry_id": entry_id,
            "item_name": entry.item_name,
            "user_id": current_user.id,
            "username": current_user.username,
            "timestamp": now_zagreb.isoformat()
        }
        await redis_client.lpush("recent_events", json.dumps(event_data))
        await redis_client.ltrim("recent_events", 0, 99)
        await redis_client.close()
    except Exception as e:
        print(f"Greška pri spremanju u Redis: {e}")
    
    db.delete(entry)
    db.commit()
    return {"detail": f"Unos s ID-em {entry_id} je uspješno obrisan"}
