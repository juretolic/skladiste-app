# Skladište App

Jednostavna aplikacija za upravljanje skladištem napravljena s FastAPI i Docker.

## Što radi

- Login/registracija korisnika
- Dodavanje robe u skladište (ulaz/izlaz)
- Pregled stanja skladišta
- Brisanje i uređivanje unosa
- Admin može vidjeti sve, obični korisnici samo svoje

## Kako pokrenuti lokalno

```bash
# Kloniraj projekt
git clone <repository-url>
cd skladiste-app

# Pokreni s Docker
docker-compose up --build
```

## Deployment na Oracle Cloud

### 1. Kreiraj VM na Oracle Cloud
- Otvori Oracle Cloud Console
- Kreiraj novu VM instancu (Ubuntu 22.04)
- Otvori port 80 u Security List

### 2. Poveži se s VM-om
```bash
ssh ubuntu@your-vm-ip
```

### 3. Kloniraj projekt
```bash
git clone https://github.com/juretolic/skladiste-app.git
cd skladiste-app
```

### 4. Pokreni deployment
```bash
chmod +x deploy.sh
./deploy.sh
```

### 5. Pristup aplikaciji
- **Web**: http://your-vm-ip
- **API docs**: http://your-vm-ip/docs

## Pristup aplikaciji

- **Web**: http://localhost:8000
- **API docs**: http://localhost:8000/docs

## Tehnologije

- FastAPI (Python)
- MySQL baza
- Redis cache
- Docker
- HTML/CSS/JS frontend

## Struktura

```
app/
├── main.py          # Glavna aplikacija
├── auth.py          # Login/registracija
├── stock.py         # Skladište API
├── models.py        # Baza podataka
└── schemas.py       # Podaci

static/
└── index.html       # Frontend

docker-compose.yml   # Lokalno pokretanje
docker-compose.prod.yml  # Produkcija
deploy.sh           # Deployment skripta
```

## API

- `POST /login` - Prijava
- `POST /register` - Registracija
- `POST /stock/entry` - Dodaj robu
- `GET /stock/list` - Lista robe
- `DELETE /stock/delete/{id}` - Obriši unos
 
