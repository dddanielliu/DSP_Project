import logging
import httpx
import os

from fastapi import FastAPI, Request, BackgroundTasks
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    AsyncMessagingApi,
    ApiClient,
    ReplyMessageRequest,
    TextMessage,
    ShowLoadingAnimationRequest
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

# --- Configuration ---
LINE_CHANNEL_ACCESS_TOKEN = "u/ezjWS++KkeWIu9okqacSsteQlV607g8+r1PynBuuoHQJwteGvXlUqXTJW6ZZ7+4I2/j1UOYP1dUSuWtTfEcXb/twJ+XOhDSCmYykaybiOQ+zUO2wkCj2pbXtbZ6LF4/k0HuIyC9OCnt6cO9Hx2TwdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "587ecb687afc71cebed169fdf2efdeb9"
GENERATE_API_URL = "http://127.0.0.1:8901/generate"

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
async_api_client = ApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

async def generate_and_reply(reply_token: str, user_text: str, user_id: str):
    """
    背景任務：呼叫 AI 並回覆
    """
    try:
        # 1. 顯示 Loading 動畫 (如果在群組可能無效，可略過)
        try:
            await line_bot_api.show_loading_animation(
                ShowLoadingAnimationRequest(chatId=user_id, loadingSeconds=20)
            )
        except Exception:
            pass

        # 2. 呼叫你的 API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GENERATE_API_URL, 
                params={"user_text": user_text}
            )
            response.raise_for_status()
            ai_reply = response.json()

        # 3. 回覆訊息
        await line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=str(ai_reply))]
            )
        )
        logger.info(f"已回覆訊息: {ai_reply}")

    except Exception as e:
        logger.error(f"背景任務錯誤: {e}")

# 關鍵修正：這裡改用 "/"，因為 LINE 是送到根目錄
@app.post("/") 
async def callback(request: Request, background_tasks: BackgroundTasks):
    # 1. 取得 Header
    signature = request.headers.get('X-Line-Signature', '')

    # 2. 取得 Body
    body = await request.body()
    body_text = body.decode('utf-8')

    # 3. 驗證簽章
    try:
        handler.parser.parse(body_text, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        return 'Invalid signature', 400

    # 4. 手動解析並放入背景執行 (為了立刻回傳 200 OK)
    events = handler.parser.parse(body_text, signature)
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            background_tasks.add_task(
                generate_and_reply,
                event.reply_token,
                event.message.text,
                event.source.user_id
            )

    return 'OK'

if __name__ == "__main__":
    import uvicorn
    # 這裡 port 改成 8900 以符合你的 log
    uvicorn.run(app, host="0.0.0.0", port=8900)