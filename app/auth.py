from fastapi import APIRouter, Depends, HTTPException, status, Request, Security
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from typing import Optional
from app.database import get_db
from app import models, schemas
from sqlalchemy import func

router = APIRouter()

# Konfiguracija za JWT
SECRET_KEY = "tajna_lozinka"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Omogućavanje Swagger token authorizacije
class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(self, tokenUrl: str):
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl})
        super().__init__(flows=flows)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=403, detail="Not authenticated")
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme")
        return token

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ✅ Dohvati trenutnog korisnika preko tokena
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
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

# ✅ Ruta za registraciju korisnika
@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Korisničko ime već postoji")
    hashed_password = get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password, is_admin=user.is_admin)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# ✅ Ruta za login korisnika
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

# ✅ Ruta za listanje svih unosa robe
@router.get("/stock/list", response_model=list[schemas.StockEntryResponse])
def list_all_stock_entries(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.StockEntry).all()

# ✅ Ruta za sažetak stanja robe po artiklima
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
        .group_by(models.StockEntry.item_name)
        .all()
    )
    return {item: quantity for item, quantity in entries}

# ✅ Ruta za unos robe (ulaz/izlaz)
@router.post("/stock/entry", response_model=schemas.StockEntryResponse)
def create_stock_entry(entry: schemas.StockEntryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_entry = models.StockEntry(
        item_name=entry.item_name,
        quantity=entry.quantity,
        entry_type=entry.entry_type,
        timestamp=datetime.utcnow()
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

# ✏️ Ruta za ažuriranje unosa robe
@router.put("/stock/update/{entry_id}", response_model=schemas.StockEntryResponse)
def update_stock_entry(entry_id: int, updated_entry: schemas.StockEntryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    entry = db.query(models.StockEntry).filter(models.StockEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Unos nije pronađen")

    entry.item_name = updated_entry.item_name
    entry.quantity = updated_entry.quantity
    entry.entry_type = updated_entry.entry_type
    entry.timestamp = datetime.utcnow()

    db.commit()
    db.refresh(entry)
    return entry

# 🗑️ Ruta za brisanje unosa robe
@router.delete("/stock/delete/{entry_id}")
def delete_stock_entry(entry_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    entry = db.query(models.StockEntry).filter(models.StockEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Unos nije pronađen")

    db.delete(entry)
    db.commit()
    return {"detail": f"Unos s ID-em {entry_id} je uspješno obrisan"}
