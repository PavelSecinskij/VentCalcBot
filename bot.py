import os
from threading import Thread
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TOKEN = os.getenv("TOKEN")

user_data = {}
PI = 3.14

# ================= БЛОК ЗАЩИТЫ БОТА ПАРОЛЕМ =================
# Множество для хранения Telegram ID пользователей, успешно прошедших проверку
authenticated_users = set()

# Твой секретный пароль. Измени значение в кавычках на свой вариант
SECRET_PASSWORD = "123132"
# ============================================================

def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("1️⃣ Кухня"), KeyboardButton("2️⃣ Котельная")],
        [KeyboardButton("🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_diameter_keyboard():
    keyboard = [
        [KeyboardButton("100"), KeyboardButton("110"), KeyboardButton("120")],
        [KeyboardButton("125"), KeyboardButton("130"), KeyboardButton("140")],
        [KeyboardButton("150"), KeyboardButton("160"), KeyboardButton("Другой")],
        [KeyboardButton("🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data[user_id] = {}
    
    # ПРОВЕРКА: Если пользователь уже вводил пароль ранее
    if user_id in authenticated_users:
        await update.message.reply_text(
            "Добро пожаловать.\n\nЧто будем проверять?",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # Если пользователя нет в списке авторизованных, требуем пароль
        user_data[user_id]["status"] = "wait_password"
        await update.message.reply_text("🔒 Доступ ограничен. Введите секретный код доступа:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # 1. ПРОВЕРКА ВВОДИМОГО ПАРОЛЯ
    if user_id in user_data and user_data[user_id].get("status") == "wait_password":
        if text == SECRET_PASSWORD:
            authenticated_users.add(user_id)  # Добавляем пользователя в белый список
            user_data[user_id] = {}          # Очищаем статус ожидания пароля
            await update.message.reply_text(
                "✅ Пароль верный! Доступ к калькулятору открыт.",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await update.message.reply_text("❌ Неверный код. Попробуйте еще раз:")
        return

    # 2. ЗАЩИТА ОТ ОБХОДА (Если пишут текст без авторизации)
    if user_id not in authenticated_users:
        user_data[user_id] = {"status": "wait_password"}
        await update.message.reply_text("🔒 Доступ ограничен. Введите секретный код доступа:")
        return

    # --- Ниже идет твоя стандартная рабочая логика расчетов ---
    if text == "🏠 Главное меню":
        user_data[user_id] = {}
        await update.message.reply_text("Что будем проверять?", reply_markup=get_main_menu_keyboard())
        return

    if user_id in user_data and "status" in user_data[user_id]:
        status = user_data[user_id]["status"]

        # ================= КУХНЯ =================
        if status == "wait_kitchen_d":
            if text == "Другой":
                user_data[user_id]["status"] = "wait_kitchen_custom_d"
                await update.message.reply_text("Введите диаметр канала в мм:")
                return
            try:
                d_mm = float(text.replace(",", "."))
                user_data[user_id]["s_calc"] = (PI * ((d_mm / 1000) ** 2)) / 4
                user_data[user_id]["d_mm"] = d_mm
                user_data[user_id]["status"] = "wait_kitchen_v"
                await update.message.reply_text("Введите среднюю скорость воздуха (м/с):", reply_markup=get_main_menu_keyboard())
            except ValueError:
                await update.message.reply_text("Выберите диаметр из кнопок или введите число:")
            return

        if status == "wait_kitchen_custom_d":
            try:
                d_mm = float(text.replace(",", "."))
                user_data[user_id]["s_calc"] = (PI * ((d_mm / 1000) ** 2)) / 4
                user_data[user_id]["d_mm"] = d_mm
                user_data[user_id]["status"] = "wait_kitchen_v"
                await update.message.reply_text("Введите среднюю скорость воздуха (м/с):")
            except ValueError:
                await update.message.reply_text("Введите диаметр числом (мм):")
            return

        if status == "wait_kitchen_v":
            try:
                v_sp = float(text.replace(",", "."))
                s_calc = user_data[user_id]["s_calc"]
                d_mm = user_data[user_id]["d_mm"]
                
                q_fact = 3600 * v_sp * s_calc
                q_norm = 90.0
                
                if q_fact >= q_norm:
                    verdict = "✅ Соответствует"
                else:
                    v_min = q_norm / (3600 * s_calc)
                    verdict = f"❌ Не соответствует\n\n💡 Должна быть скорость V ≥ {v_min:.2f} м/с"
                
                report = (
                    f"📊 Результат расчета\n\n"
                    f"Диаметр канала: {d_mm:.0f} мм\n\n"
                    f"Площадь сечения S = {s_calc:.4f} м²\n\n"
                    f"Скорость V = {v_sp} м/с\n\n"
                    f"Количество удаляемого воздуха Q = {q_fact:.2f} м³/ч\n\n"
                    f"Норма Q ≥ {q_norm:.0f} м³/ч\n\n"
                    f"{verdict}"
                )
                await update.message.reply_text(report, reply_markup=get_main_menu_keyboard())
                user_data[user_id] = {}
            except ValueError:
                await update.message.reply_text("Введите скорость числом (м/с):")
            return

        # ================= КОТЕЛЬНАЯ =================
        if status == "wait_kotel_d":
            if text == "Другой":
                user_data[user_id]["status"] = "wait_kotel_custom_d"
                await update.message.reply_text("Введите диаметр канала в мм:")
                return
            try:
                d_mm = float(text.replace(",", "."))
                user_data[user_id]["s_calc"] = (PI * ((d_mm / 1000) ** 2)) / 4
                user_data[user_id]["d_mm"] = d_mm
                user_data[user_id]["status"] = "wait_kotel_v"
                await update.message.reply_text("Введите скорость:", reply_markup=get_main_menu_keyboard())
            except ValueError:
                await update.message.reply_text("Выберите диаметр из кнопок или введите число:")
            return

        if status == "wait_kotel_custom_d":
            try:
                d_mm = float(text.replace(",", "."))
                user_data[user_id]["s_calc"] = (PI * ((d_mm / 1000) ** 2)) / 4
                user_data[user_id]["d_mm"] = d_mm
                user_data[user_id]["status"] = "wait_kotel_v"
                await update.message.reply_text("Введите скорость:")
            except ValueError:
                await update.message.reply_text("Введите диаметр числом:")
            return

        if status == "wait_kotel_v":
            try:
                user_data[user_id]["v_sp"] = float(text.replace(",", "."))
                user_data[user_id]["status"] = "wait_kotel_vol"
                await update.message.reply_text("Введите объем помещения:")
            except ValueError:
                await update.message.reply_text("Введите скорость числом:")
            return

        if status == "wait_kotel_vol":
            try:
                vol = float(text.replace(",", "."))
                s_calc = user_data[user_id]["s_calc"]
                v_sp = user_data[user_id]["v_sp"]
                d_mm = user_data[user_id]["d_mm"]
                
                q_fact = 3600 * v_sp * s_calc
                k_fact = q_fact / vol
                
                if k_fact >= 3.0:
                    verdict = "✅ Соответствует"
                else:
                    q_needed = vol * 3.0
                    v_min = q_needed / (3600 * s_calc)
                    verdict = f"❌ Не соответствует\n\n💡 Должна быть скорость V ≥ {v_min:.2f} м/с"
                
                report = (
                    f"📊 Результат расчета\n\n"
                    f"Диаметр канала: {d_mm:.0f} мм\n\n"
                    f"Площадь сечения S = {s_calc:.4f} м²\n\n"
                    f"Скорость V = {v_sp} м/с\n\n"
                    f"Расход воздуха Q = {q_fact:.2f} м³/ч\n\n"
                    f"Объем помещения = {vol:.1f} м³\n\n"
                    f"Кратность K = {k_fact:.2f}\n\n"
                    f"Норма K ≥ 3\n\n"
                    f"{verdict}"
                )
                await update.message.reply_text(report, reply_markup=get_main_menu_keyboard())
                user_data[user_id] = {}
            except ValueError:
                await update.message.reply_text("Введите объем числом:")
            return

    if text == "1️⃣ Кухня":
        user_data[user_id] = {"status": "wait_kitchen_d"}
        await update.message.reply_text("Выберите или введите диаметр канала (мм):", reply_markup=get_diameter_keyboard())
    elif text == "2️⃣ Котельная":
        user_data[user_id] = {"status": "wait_kotel_d"}
        await update.message.reply_text("Выберите или введите диаметр канала (мм):", reply_markup=get_diameter_keyboard())
    else:
        await update.message.reply_text("Что будем проверять?", reply_markup=get_main_menu_keyboard())


# ================= ВЕБ-СЕРВЕР FLASK ДЛЯ УДЕРЖАНИЯ ПОРТА НА RENDER =================
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Бот успешно запущен и защищен паролем!"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host='0.0.0.0', port=port)


def main():
    # Запускаем Flask-сервер параллельно в фоновом потоке
    Thread(target=run_flask).start()

    # Основной запуск Telegram-бота
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("ВентКалькулятор успешно перезапущен...")
    app.run_polling()

if __name__ == "__main__":
    main()