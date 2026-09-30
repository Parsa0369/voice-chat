from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()

@router.get("/hello")
async def hello():
    return RedirectResponse("/", status_code=307)
