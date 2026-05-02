"""飞书Webhook路由"""

from fastapi import APIRouter, Request

router = APIRouter()

# FeishuBot实例在app.py中注入
_bot = None


def set_bot(bot) -> None:
    global _bot
    _bot = bot


@router.post("/webhook/feishu")
async def feishu_webhook(request: Request):
    """接收飞书Webhook事件"""
    if _bot is None:
        return {"status": "error", "message": "飞书机器人未初始化"}

    body = await request.json()
    result = await _bot.handle_event(body)
    return result
