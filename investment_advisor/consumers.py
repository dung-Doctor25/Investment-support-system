# your_app/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async # Rất quan trọng!

# --- Import hàm Gemini của bạn ---
# Giả sử bạn đặt hàm call_gemini trong file "gemini_utils.py"
# (Bạn cần tạo file này và dán hàm call_gemini vào)
from .gemini_utils import call_gemini 

# --- Wrapper để gọi hàm đồng bộ (blocking) ---
# Hàm call_gemini của bạn là hàm đồng bộ (blocking).
# Gọi nó trực tiếp trong consumer (async) sẽ làm treo server.
# @sync_to_async sẽ chạy hàm đó trong một thread riêng.
@sync_to_async
def async_call_gemini(prompt: str) -> str:
    return call_gemini(prompt)


class ChatConsumer(AsyncWebsocketConsumer):
    # Được gọi khi client kết nối
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_success',
            'message': 'Xin chào! Bạn đã kết nối với Finance AI Assistant.'
        }))

    # Được gọi khi client ngắt kết nối
    async def disconnect(self, close_code):
        print(f"WebSocket đã đóng với code: {close_code}", flush=True)

    # Được gọi khi client gửi tin nhắn
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            prompt = text_data_json['message']

            # Gửi tin nhắn "Bot đang gõ..." về client
            await self.send(text_data=json.dumps({
                'type': 'bot_loading'
            }))

            # Gọi Gemini một cách an toàn (bất đồng bộ)
            bot_response = await async_call_gemini(prompt)

            # Gửi phản hồi của bot về client
            await self.send(text_data=json.dumps({
                'type': 'bot_response',
                'message': bot_response
            }))
            
        except Exception as e:
            # Gửi lỗi về client nếu có
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))