import httpx
from fastapi import APIRouter, Request, Response, Depends, status
from api_gateway.auth import verify_jwt_token

router = APIRouter()

# تعيين عناوين الخدمات الداخلية
SERVICES = {
    "user": "http://localhost:8001",
    "order": "http://localhost:8002",
    "liquidity": "http://localhost:8003",
    "ai": "http://localhost:8004",
}

async def forward_request(
    service_url: str, 
    path: str, 
    request: Request, 
    user_data: dict = None
) -> Response:
    """
    توجيه الطلب الشفاف (Reverse Proxy) إلى الخدمة المعنية
    """
    url = f"{service_url}/{path}"
    headers = dict(request.headers)
    
    # تحويل بيانات المستخدم الموثقة لخدمات الخلفية
    if user_data:
        headers["X-User-ID"] = str(user_data["user_id"])
        headers["X-User-Role"] = str(user_data["role"])
        
    # استبعاد رأس Host المتصل بالبوابة
    headers.pop("host", None)

    async with httpx.AsyncClient() as client:
        try:
            body = await request.body()
            proxy_res = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
                content=body,
                timeout=10.0
            )
            return Response(
                content=proxy_res.content,
                status_code=proxy_res.status_code,
                headers=dict(proxy_res.headers)
            )
        except httpx.RequestError as exc:
            return Response(
                content=f'{{"detail": "الخدمة غير متاحة حالياً: {exc}"}}',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json"
            )

# --- المسارات وتوجيه الطلبات ---

# 1. مسارات خدمة المستخدمين (تسجيل الدخول يمر بدون توثيق)
@router.api_route("/users/login", methods=["POST"])
@router.api_route("/users/register", methods=["POST"])
async def auth_routes(request: Request):
    path = request.url.path.replace("/api/v1/users/", "")
    return await forward_request(SERVICES["user"], path, request)

@router.api_route("/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def user_service_proxy(path: str, request: Request, user: dict = Depends(verify_jwt_token)):
    return await forward_request(SERVICES["user"], path, request, user_data=user)

# 2. مسارات خدمة الأوامر (تتطلب توثيق)
@router.api_route("/orders/{path:path}", methods=["GET", "POST", "DELETE"])
async def order_service_proxy(path: str, request: Request, user: dict = Depends(verify_jwt_token)):
    return await forward_request(SERVICES["order"], path, request, user_data=user)

# 3. مسارات خدمة السيولة
@router.api_route("/liquidity/{path:path}", methods=["GET"])
async def liquidity_service_proxy(path: str, request: Request, user: dict = Depends(verify_jwt_token)):
    return await forward_request(SERVICES["liquidity"], path, request, user_data=user)

# 4. مسارات محرك الذكاء الاصطناعي
@router.api_route("/ai/{path:path}", methods=["GET", "POST"])
async def ai_engine_proxy(path: str, request: Request, user: dict = Depends(verify_jwt_token)):
    return await forward_request(SERVICES["ai"], path, request, user_data=user)
