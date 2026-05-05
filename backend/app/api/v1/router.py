from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.properties import router as properties_router
from app.api.v1.endpoints.users import router as users_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(properties_router)
api_router.include_router(users_router)
