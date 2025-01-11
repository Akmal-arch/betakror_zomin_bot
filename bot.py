import telebot
from telebot import types
import schedule
import time
import threading
from datetime import datetime, timedelta
import json
import os
import uuid

API_TOKEN = '7152711739:AAH4qQxkqJrha_jL1tY1nvswRFePg1w21nE'
USER_ID = '1992943760'
CHANNEL_ID = '-1001141083846'

bot = telebot.TeleBot(API_TOKEN)

schedules = []
ads_data = {}

# Load and save schedules to JSON file
def save_schedules():
    with open('schedules.json', 'w') as f:
        json.dump(schedules, f)

def load_schedules():
    global schedules
    if os.path.exists('schedules.json'):
        with open('schedules.json', 'r') as f:
            schedules = json.load(f)

# Function to send scheduled messages with optional media
def send_message(schedule_item):
    try:
        if schedule_item.get('file_id'):
            if schedule_item['media_type'] == 'photo':
                bot.send_photo(CHANNEL_ID, schedule_item['file_id'], caption=schedule_item['message'], parse_mode='HTML')
            elif schedule_item['media_type'] == 'video':
                bot.send_video(CHANNEL_ID, schedule_item['file_id'], caption=schedule_item['message'], parse_mode='HTML')
            elif schedule_item['media_type'] == 'document':
                bot.send_document(CHANNEL_ID, schedule_item['file_id'], caption=schedule_item['message'], parse_mode='HTML')
        else:
            bot.send_message(CHANNEL_ID, schedule_item['message'], parse_mode='HTML')

        schedule_item['sent'] += 1
        if schedule_item['sent'] >= schedule_item['max_sends']:
            schedules.remove(schedule_item)
        save_schedules()
    except Exception as e:
        print(f"Error sending message: {e}")
        bot.send_message(USER_ID, f"❌ Error sending message to channel: {e}")

# Schedule job based on type
def schedule_job(schedule_item):
    schedule_time = datetime.strptime(schedule_item['time'], '%H:%M').time()
    now = datetime.now()

    # Adjust to schedule for the next day if the time has already passed today
    if schedule_time <= now.time():
        schedule_date = (now + timedelta(days=1)).date()
    else:
        schedule_date = now.date()

    schedule_datetime = datetime.combine(schedule_date, schedule_time)

    schedule_type = schedule_item['type']
    if schedule_type == 'one_time':
        schedule.every().day.at(schedule_item['time']).do(send_message, schedule_item)
    elif schedule_type == 'one_week_every_day':
        for _ in range(7):
            schedule.every().day.at(schedule_item['time']).do(send_message, schedule_item)
    elif schedule_type == 'one_week_every_other_day':
        for i in range(0, 7, 2):
            schedule.every(i).days.at(schedule_item['time']).do(send_message, schedule_item)
    elif schedule_type == 'one_month_every_day':
        for _ in range(30):
            schedule.every().day.at(schedule_item['time']).do(send_message, schedule_item)
    elif schedule_type == 'one_month_every_other_day':
        for i in range(0, 30, 2):
            schedule.every(i).days.at(schedule_item['time']).do(send_message, schedule_item)

    print(f"Scheduled message for: {schedule_datetime}")


# Scheduler thread
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Main menu keyboard
def get_main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    schedule_button = types.KeyboardButton("🗓️ Post Joylashtirish")
    status_button = types.KeyboardButton("📊 Statusni ko'rish")
    markup.add(schedule_button, status_button)
    return markup

# Start command handler
@bot.message_handler(commands=['start'])
def start(message):
    if str(message.from_user.id) != USER_ID:
        bot.send_message(message.chat.id, "❌ Unauthorized user.")
        return
    bot.send_message(
        message.chat.id,
        "👋 @betakror_zomin kanalining reklama avtomatlashtirish xizmatiga, Xush kelibsiz!\n\nBoshlash uchun quyidagilardan birini tanlang:",
        reply_markup=get_main_menu_keyboard()
    )

# Schedule ad command handler
@bot.message_handler(func=lambda m: m.text == "🗓️ Post Joylashtirish")
def schedule_command(message):
    if str(message.from_user.id) != USER_ID:
        bot.send_message(message.chat.id, "❌ Unauthorized user.")
        return
    msg = bot.send_message(message.chat.id, "Postning matnini kiriting:")
    bot.register_next_step_handler(msg, handle_ad_text)

# Handle ad text input
def handle_ad_text(message):
    ad_message = message.text
    msg = bot.send_message(message.chat.id, "Endi postning media fayllarini kiriting (rasm, video, document), yoki o'tkazib yuborish uchun 'skip' deb yozing:")
    bot.register_next_step_handler(msg, lambda m: handle_ad_media(m, ad_message))

# Handle ad media input
def handle_ad_media(message, ad_message):
    file_id = None
    media_type = None

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    elif message.document:
        file_id = message.document.file_id
        media_type = 'document'
    elif message.text.lower() == 'skip':
        pass
    else:
        bot.send_message(message.chat.id, "❌ Invalid media type. Please send a photo, video, or document, or type 'skip'.")
        return

    # Create a unique ID for this ad
    ad_id = str(uuid.uuid4())

    # Store ad data in the dictionary
    ads_data[ad_id] = {
        'message': ad_message,
        'file_id': file_id,
        'media_type': media_type
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Bir Martta", callback_data=f"{ad_id}|one_time"))
    markup.add(types.InlineKeyboardButton("Bir Hafta Har Kuni", callback_data=f"{ad_id}|one_week_every_day"))
    markup.add(types.InlineKeyboardButton("Bir Hafta 2 Kunda Bir (3 kun)", callback_data=f"{ad_id}|one_week_every_other_day"))
    markup.add(types.InlineKeyboardButton("Bir Oy Har Kuni", callback_data=f"{ad_id}|one_month_every_day"))
    markup.add(types.InlineKeyboardButton("Bir Oy 2 Kunda Bir (15 kun)", callback_data=f"{ad_id}|one_month_every_other_day"))

    bot.send_message(message.chat.id, "Tarifni Tanlang:", reply_markup=markup)

# Handle schedule type selection
@bot.callback_query_handler(func=lambda call: call.data.split('|')[1] in [
    "one_time", "one_week_every_day", "one_week_every_other_day", "one_month_every_day", "one_month_every_other_day"
])
def handle_schedule_type(call):
    ad_id, schedule_type = call.data.split('|')
    
    # Retrieve ad data using the unique ID
    ad_data = ads_data.get(ad_id)
    
    if ad_data:
        ad_message = ad_data['message']
        file_id = ad_data['file_id']
        media_type = ad_data['media_type']
        
        bot.answer_callback_query(call.id)
        time_msg = bot.send_message(call.message.chat.id, "Postni jonatish vaqtini kiriting (HH:MM format):")
        bot.register_next_step_handler(time_msg, lambda m: process_time(m, ad_message, file_id, media_type, schedule_type))
    else:
        bot.send_message(call.message.chat.id, "❌ Ad data not found.")


# Process time input
def process_time(message, ad_message, file_id, media_type, schedule_type):
    schedule_time = message.text.strip()
    try:
        datetime.strptime(schedule_time, '%H:%M')
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid time format. Please use HH:MM.")
        return

    schedule_item = {
        'message': ad_message,
        'time': schedule_time,
        'type': schedule_type,
        'sent': 0,
        'max_sends': 1,
        'file_id': file_id,
        'media_type': media_type
    }

    schedules.append(schedule_item)
    schedule_job(schedule_item)
    save_schedules()
    bot.send_message(message.chat.id, "✅ Post Muvvaffaqiyatli Rejalashtirildi!")

# View status command handler
@bot.message_handler(func=lambda m: m.text == "📊 Statusni ko'rish")
def status_command(message):
    if str(message.from_user.id) != USER_ID:
        bot.send_message(message.chat.id, "❌ Unauthorized user.")
        return
    status_message = "📋 Aktiv Rejalashtirilgan Postlar:\n\n"
    for schedule_item in schedules:
        status_message += f"📝 Matni: {schedule_item['message']}\n\n\n⏰Vaqti: {schedule_item['time']} \n📬 Jo'natildi: {schedule_item['sent']}/{schedule_item['max_sends']}\n\n"
    bot.send_message(message.chat.id, status_message or "Aktiv postlar yoq.")

# Main entry point
if __name__ == '__main__':
    load_schedules()
    threading.Thread(target=run_scheduler).start()
    bot.polling(none_stop=True)