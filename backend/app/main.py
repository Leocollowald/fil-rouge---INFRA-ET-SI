from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url=None,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend" / "static"), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "frontend" / "templates")

app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/annonces", response_class=HTMLResponse)
def annonces(request: Request):
    return templates.TemplateResponse("properties/list.html", {"request": request})


@app.get("/annonces/{property_id}", response_class=HTMLResponse)
def annonce_detail(request: Request, property_id: str):
    return templates.TemplateResponse("properties/detail.html", {"request": request, "property_id": property_id})


@app.get("/connexion", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@app.get("/inscription", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard/index.html", {"request": request})
