from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api_gateway.router import router as api_router
from api_gateway.websocket_proxy import ws_router

app = FastAPI(
    title=f"{settings.PROJECT_NAME} - API Gateway",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. تضمين مسارات HTTP
app.include_router(api_router, prefix=settings.API_V1_STR)

# 2. تضمين مسارات WebSockets
app.include_router(ws_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api_gateway"}
