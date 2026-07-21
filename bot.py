import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# 启用日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 从环境变量中读取密钥（安全做法）
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CX = os.environ.get("GOOGLE_CX")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """当用户发送 /start 时触发"""
    await update.message.reply_text('欢迎使用纯净搜索机器人！\n直接向我发送你想搜索的关键词，我会通过 Google 帮你在 Telegram 公开渠道中检索（已强制开启安全过滤，自动屏蔽不健康内容）。')

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户发送的文本并调用 Google 搜索"""
    keyword = update.message.text.strip()
    if not keyword:
        return

    await update.message.reply_text(f'🔍 正在为您纯净搜索: "{keyword}" ...')

    # 核心：组合 Google 搜索语法，限定 t.me 域名
    search_query = f"{keyword} site:t.me"
    
    # 构造 Google API 请求参数
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": search_query,
        "safe": "active"  # 核心：在代码层面再次强制激活高强度安全过滤
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        items = data.get("items", [])
        if not items:
            await update.message.reply_text("❌ 未找到相关结果，或结果已被安全过滤。")
            return

        # 排版搜索结果
        reply_lines = [f"💡 关于 \"{keyword}\" 的纯净搜索结果：\n"]
        for idx, item in enumerate(items[:5], 1):  # 只取前 5 条最相关的结果
            title = item.get("title", "未知标题")
            link = item.get("link", "")
            snippet = item.get("snippet", "").replace("\n", " ")
            
            # 过滤掉非 t.me 的干扰链接（如果有的话）
            if "t.me" in link:
                reply_lines.append(f"{idx}. **[{title}]({link})**")
                reply_lines.append(f"   _{snippet}_\n")

        reply_text = "\n".join(reply_lines)
        await update.message.reply_text(reply_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"搜索出错: {e}")
        await update.message.reply_text("❌ 搜索服务暂时出现问题，请稍后再试。")

def main() -> None:
    """启动机器人"""
    if not all([TOKEN, GOOGLE_API_KEY, GOOGLE_CX]):
        logger.error("环境变量配置不完整！请检查 Render 的 Environment Variables 设置。")
        return

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    # Render 上运行背景服务需要保持在前台轮询
    application.run_polling()

if __name__ == '__main__':
    main()
