import os
import logging
import asyncio
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# 启用日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 环境变量
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CX = os.environ.get("GOOGLE_CX")

# 防休眠伪 HTTP 服务
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

async def start(update: Update, context):
    await update.message.reply_text('欢迎使用纯净搜索机器人！\n发送关键词，我将为您搜索经过安全过滤的 Telegram 公开内容。')

async def search(update: Update, context):
    keyword = update.message.text.strip()
    if not keyword:
        return

    await update.message.reply_text(f'🔍 正在为您纯净搜索: "{keyword}" ...')
    search_query = f"{keyword} site:t.me"
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": search_query,
        "safe": "active"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            await update.message.reply_text("❌ 未找到相关结果，或结果已被安全过滤。")
            return

        reply_lines = [f"💡 关于 \"{keyword}\" 的纯净搜索结果：\n"]
        for idx, item in enumerate(items[:5], 1):
            title = item.get("title", "未知标题")
            link = item.get("link", "")
            snippet = item.get("snippet", "").replace("\n", " ")
            if "t.me" in link:
                reply_lines.append(f"{idx}. **[{title}]({link})**\n   _{snippet}_\n")

        reply_text = "\n".join(reply_lines)
        await update.message.reply_text(reply_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"搜索出错: {e}")
        await update.message.reply_text("❌ 搜索服务暂时出现问题，请稍后再试。")

def main():
    if not all([TOKEN, GOOGLE_API_KEY, GOOGLE_CX]):
        logger.error("环境变量配置不完整！")
        return

    # 在后台线程启动 HTTP 端口，维持 Render 的 Web Service 存活
    t = Thread(target=run_http_server, daemon=True)
    t.start()

    # 启动机器人轮询
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    application.run_polling()

if __name__ == '__main__':
    main()
