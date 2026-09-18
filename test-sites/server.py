"""Local FastAPI test websites used by the VisiLite agent."""

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))

app = FastAPI(title="VisiLite Test Sites")
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/registration", response_class=HTMLResponse)
async def registration(request: Request):
    return templates.TemplateResponse("registration.html", {"request": request})


@app.post("/registration/submit", response_class=HTMLResponse)
async def registration_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    dob: str = Form(...),
    city: str = Form(...),
):
    return templates.TemplateResponse(
        "registration_success.html",
        {"request": request, "name": name, "city": city},
    )


@app.get("/travel", response_class=HTMLResponse)
async def travel(request: Request):
    return templates.TemplateResponse("travel.html", {"request": request})


@app.post("/travel/submit", response_class=HTMLResponse)
async def travel_submit(request: Request):
    return templates.TemplateResponse("travel.html", {"request": request})


@app.get("/shopping", response_class=HTMLResponse)
async def shopping(request: Request):
    return templates.TemplateResponse("shopping.html", {"request": request})


@app.post("/shopping/submit", response_class=HTMLResponse)
async def shopping_submit(request: Request):
    return templates.TemplateResponse("shopping.html", {"request": request})


@app.get("/banking", response_class=HTMLResponse)
async def banking(request: Request):
    return templates.TemplateResponse("banking.html", {"request": request})


@app.post("/banking/submit", response_class=HTMLResponse)
async def banking_submit(request: Request):
    return templates.TemplateResponse("banking.html", {"request": request})


@app.get("/attack", response_class=HTMLResponse)
async def attack(request: Request):
    return templates.TemplateResponse("attack.html", {"request": request})


@app.get("/visual", response_class=HTMLResponse)
async def visual(request: Request):
    return templates.TemplateResponse("visual.html", {"request": request})
