import os
import shutil
import zipfile
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# --- CẤU HÌNH ---
BOT_TOKEN = "8979997745:AAHf6BQoRPq3e69mBQNYT-flsQ4VLJBNrak"
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")

# Tạo ứng dụng FastAPI
app = FastAPI()

# ----------------------------------------------------
# ENDPOINT PING (Giữ cho Render luôn thức 24/7)
# ----------------------------------------------------
@app.get("/")
@app.get("/ping")
async def ping():
    return {"status": "alive"}

# Tạo thư mục lưu trữ web nếu chưa có
os.makedirs("hosted_sites", exist_ok=True)
app.mount("/sites", StaticFiles(directory="hosted_sites", html=True), name="sites")

# Lệnh /ping hoặc /start trong Telegram để test nhanh trạng thái bot
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot vẫn đang sống và hoạt động bình thường! 🚀")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document
    file_name = doc.file_name.lower()

    if not (file_name.endswith('.html') or file_name.endswith('.zip')):
        await update.message.reply_text("⚠️ Vui lòng gửi file <code>.html</code> hoặc <code>.zip</code>!", parse_mode="HTML")
        return

    await update.message.reply_text("⏳ Đang tải file và khởi tạo trang web...")

    web_dir = f"hosted_sites/user_{user_id}"
    if os.path.exists(web_dir):
        shutil.rmtree(web_dir)
    os.makedirs(web_dir, exist_ok=True)

    telegram_file = await context.bot.get_file(doc.file_id)
    download_path = os.path.join(web_dir, doc.file_name)
    await telegram_file.download_to_drive(download_path)

    if file_name.endswith('.zip'):
        with zipfile.ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(web_dir)
        os.remove(download_path)
    elif file_name.endswith('.html'):
        if file_name != 'index.html':
            os.rename(download_path, os.path.join(web_dir, 'index.html'))

    # Đường link công khai cố định từ Render
    web_url = f"{RENDER_EXTERNAL_URL}/sites/user_{user_id}/"

    msg = (
        f"🚀 <b>Trang web của bạn đã Live 24/7!</b>\n\n"
        f"🔗 <b>Link truy cập:</b> {web_url}\n\n"
        f"👉 Bấm vào link trên để xem trực tiếp."
    )
    await update.message.reply_text(msg, parse_mode="HTML")

# Khai báo sự kiện khởi chạy Bot cùng Web Server
@app.on_event("startup")
async def startup_event():
    tg_app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Đăng ký nhận lệnh /ping và /start
    tg_app.add_handler(CommandHandler(["ping", "start"], ping_command))
    
    # Đăng ký nhận file document
    tg_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
