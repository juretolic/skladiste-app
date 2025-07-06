from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app import models, database
from app.auth import router as auth_router
from app.stock import router as stock_router

# Kreiranje tablica u bazi ako ne postoje
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# Dodavanje CORS middleware-a
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # možeš ovdje staviti frontend URL ako želiš ograničiti pristup (npr. "http://localhost:5500")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount statičkih datoteka
app.mount("/static", StaticFiles(directory="static"), name="static")

# Registracija ruta
app.include_router(auth_router, tags=["Auth"])
app.include_router(stock_router, tags=["Stock"])

# Ruta za serviranje index.html
@app.get("/")
def root():
    return FileResponse("static/index.html")

# Test ruta (nije obavezna, ali korisna za testiranje)
@app.get("/api")
def api_root():
    return {"message": "Dobrodošli u skladište-app API!"}

