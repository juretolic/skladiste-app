# Skladište App

Jednostavna aplikacija za upravljanje skladištem napravljena s FastAPI i Docker.

## Što radi

- Login/registracija korisnika
- Dodavanje robe u skladište (ulaz/izlaz)
- Pregled stanja skladišta
- Brisanje i uređivanje unosa
- Admin može vidjeti sve, obični korisnici samo svoje

## Kako pokrenuti

```bash
# Kloniraj projekt
git clone <repository-url>
cd skladiste-app

# Pokreni s Docker
docker-compose up --build
```

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
```

## API

- `POST /login` - Prijava
- `POST /register` - Registracija
- `POST /stock/entry` - Dodaj robu
- `GET /stock/list` - Lista robe
- `DELETE /stock/delete/{id}` - Obriši unos

## Autori

Student - Upravljanje podacima 2024 