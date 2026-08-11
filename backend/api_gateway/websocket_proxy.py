import asyncio
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState
import logging

logger = logging.getLogger("gateway_ws_proxy")
ws_router = APIRouter()

# عنوان خدمة تدفق البيانات الحية الداخلي
DATA_PIPELINE_WS_URL = "ws://localhost:8005/ws/market-data"

async def forward_stream(source_ws, target_ws):
    """
    دالة مساعدة لنقل الرسائل المستمرة من مصدر إلى هدف
    """
    try:
        while True:
            # استقبال الرسالة من الطرف الأول
            if isinstance(source_ws, WebSocket):
                data = await source_ws.receive_text()
            else:
                data = await source_ws.recv()

            # إرسال الرسالة إلى الطرف الثاني
            if isinstance(target_ws, WebSocket):
                await target_ws.send_text(data)
            else:
                await target_ws.send(data)

    except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
        # قطع الاتصال الطبيعي
        pass
    except Exception as e:
        logger.error(f"خطأ أثناء تمرير بيانات الـ WebSocket: {e}")


@ws_router.websocket("/ws/market-stream")
async def market_data_websocket_proxy(websocket: WebSocket, symbol: str = "BTC-USDT"):
    """
    نقطة النهاية التي تتصل بها الواجهة الأمامية (Client)
    مثال: ws://localhost:8000/api/v1/ws/market-stream?symbol=BTC-USDT
    """
    # 1. قبول اتصال العميل من الواجهة
    await websocket.accept()

    # 2. إنشاء الاتصال الداخلي مع خدمة البيانات الحية
    target_uri = f"{DATA_PIPELINE_WS_URL}?symbol={symbol}"

    try:
        async with websockets.connect(target_uri) as internal_ws:
            # 3. تشغيل مهمتين متوازيتين للاتصال المزدوج (Client <-> Gateway <-> Backend)
            client_to_backend = asyncio.create_task(
                forward_stream(websocket, internal_ws)
            )
            backend_to_client = asyncio.create_task(
                forward_stream(internal_ws, websocket)
            )

            # الانتظار لحين انتهاء أو انقطاع أحدهما
            done, pending = await asyncio.wait(
                [client_to_backend, backend_to_client],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # إلغاء المهمة المتبقية فور انقطاع الاتصال
            for task in pending:
                task.cancel()

    except Exception as exc:
        logger.error(f"فشل الاتصال بخدمة البيانات الداخلية: {exc}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


@ws_router.websocket("/ws/user-orders")
async def user_orders_websocket_proxy(websocket: WebSocket, token: str):
    """
    تمرير إشعارات الأوامر الخاصة بالمستخدم (تتطلب توثيق Token عبر Query Parameter)
    """
    await websocket.accept()
    
    # يمكنك إضافة التحقق من الـ Token هنا قبل التمرير
    # user_data = decode_jwt(token)
    
    target_uri = f"ws://localhost:8002/ws/orders?token={token}"

    try:
        async with websockets.connect(target_uri) as internal_ws:
            client_to_backend = asyncio.create_task(forward_stream(websocket, internal_ws))
            backend_to_client = asyncio.create_task(forward_stream(internal_ws, websocket))

            done, pending = await asyncio.wait(
                [client_to_backend, backend_to_client],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

    except Exception as exc:
        logger.error(f"فشل الاتصال بخدمة الأوامر الحية: {exc}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
