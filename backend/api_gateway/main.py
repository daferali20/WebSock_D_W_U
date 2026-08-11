from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api_gateway.router import router as api_router

app = FastAPI(
    title=f"{settings.PROJECT_NAME} - API Gateway",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# إعداد سياسات الاتصال العابر للمواقع (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # يمكن تحديد النطاقات المسموحة لاحقاً
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تضمين موجه المسارات بالبادئة الرسمية للـ API
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api_gateway"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
