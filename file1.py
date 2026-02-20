import telebot
import requests
import json
import time
import os
import datetime
import random
import threading

# ضع توكن البوت الخاص بك هنا
TOKEN = "7987425397:"

# تفعيل تعدد المسارات لدعم مئات المستخدمين في نفس الوقت بدون تأخير
bot = telebot.TeleBot(TOKEN, num_threads=50)

# الرابط الخاص بك
ES_URL = "http://67.217.59.246:9200/matcher/_search"

last_search_times = {}
LIMITS_FILE = "random_limits.json"

# قفل برمجي لحماية ملفات الجيسون من التلف عند ضغط المستخدمين
file_lock = threading.Lock()

def get_iraq_date():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')

def check_random_limit(user_id):
    current_date = get_iraq_date()

    with file_lock:
        if os.path.exists(LIMITS_FILE):
            with open(LIMITS_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {"date": current_date, "users": {}}

            if data.get("date") != current_date:
                os.remove(LIMITS_FILE)
                data = {"date": current_date, "users": {}}
        else:
            data = {"date": current_date, "users": {}}

        user_str = str(user_id)
        user_count = data["users"].get(user_str, 0)

        if user_count >= 100:
            return False

        data["users"][user_str] = user_count + 1

        with open(LIMITS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    return True

def log_search(user_id, name, search_type, query):
    log_entry = {
        "id": user_id,
        "name": name,
        "type": search_type,
        "query": query
    }
    filename = "logs.json"

    with file_lock:
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as file:
                    try:
                        logs = json.load(file)
                    except json.JSONDecodeError:
                        logs = []
            else:
                logs = []

            logs.append(log_entry)
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(logs, file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error logging: {e}")

@bot.message_handler(commands=['start', 'help'])
def send_instructions(message):
    instructions = (
        "<b>Welcome.</b>\n\n"
        "<b>We have 4,606,063,150 emails</b>\n\n"
        "<b>Commands:</b>\n"
        "<b>/email {target}</b>\n"
        "<b>/pass {target}</b>\n"
        "<b>/random {count}</b>"
    )
    bot.reply_to(message, instructions, parse_mode="HTML")

@bot.message_handler(commands=['random'])
def handle_random(message):
    user_id = message.from_user.id
    current_time = time.time()

    if user_id in last_search_times and (current_time - last_search_times[user_id]) < 3:
        return
    last_search_times[user_id] = current_time

    try:
        count_str = message.text.split(" ", 1)[1].strip()
        count = int(count_str)
    except (IndexError, ValueError):
        bot.reply_to(message, "<b>Error:</b> Invalid count. Use /random {Number}.", parse_mode="HTML")
        return

    if count > 149:
        bot.reply_to(message, "<b>Error:</b> Maximum allowed count is 149.", parse_mode="HTML")
        return
    if count <= 0:
        return

    if not check_random_limit(user_id):
        bot.reply_to(message, "<b>Error:</b> Don't be gay, your daily limit is over, come back tomorrow", parse_mode="HTML")
        return

    log_search(user_id, message.from_user.first_name, "random", str(count))

    random_chars = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=2))
    random_skip = random.randint(0, 9000)

    params = {
        'q': f'email:{random_chars}*',
        'from': random_skip,
        'size': count,
        'pretty': 'true'
    }

    start_time = time.time()
    try:
        response = requests.get(ES_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        # طباعة الخطأ في التيرمنال للمدير فقط
        print(f"Backend Error [Random]: {e}")
        # رسالة مبهمة وعامة للمستخدم
        bot.reply_to(message, "<b>Error:</b> Service is currently unavailable. Please try again later.", parse_mode="HTML")
        return

    end_time = time.time()
    search_duration = round(end_time - start_time, 4)

    hits_data = data.get('hits', {}).get('hits', [])
    total_results = len(hits_data)

    telegram_header = (
        "<blockquote>\n"
        f"<b>Time:</b> {search_duration}s\n"
        f"<b>Results:</b> {total_results}\n"
        "</blockquote>\n"
    )

    if total_results == 0:
        bot.reply_to(message, telegram_header + "No results found.", parse_mode="HTML")
        return

    formatted_message = ""
    file_content = f"Time: {search_duration}s\nResults: {total_results}\n\n"

    for hit in hits_data:
        source = hit.get('_source', {})
        email = source.get('email', 'N/A')
        password = source.get('password', 'N/A')

        formatted_message += f"<b>Email:</b> <code>{email}</code>\n<b>Password:</b> <code>{password}</code>\n\n"
        file_content += f"Email: {email}\nPassword: {password}\n\n"

    if total_results <= 10:
        bot.reply_to(message, telegram_header + formatted_message.strip(), parse_mode="HTML")
    else:
        filename = f"random_{user_id}_{int(time.time())}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(file_content.strip())

        with open(filename, "rb") as f:
            bot.send_document(
                message.chat.id, 
                f, 
                caption=telegram_header.strip(),
                parse_mode="HTML",
                reply_to_message_id=message.message_id
            )

        os.remove(filename)

@bot.message_handler(commands=['email', 'pass'])
def handle_search(message):
    user_id = message.from_user.id
    current_time = time.time()

    if user_id in last_search_times and (current_time - last_search_times[user_id]) < 3:
        return

    last_search_times[user_id] = current_time

    command = message.text.split()[0]
    try:
        query_value = message.text.split(" ", 1)[1].strip()
    except IndexError:
        bot.reply_to(message, "<b>Error:</b> Missing search parameter.", parse_mode="HTML")
        return

    if command == '/email':
        query_value = query_value.lower()
        if '@' not in query_value:
            bot.reply_to(message, "<b>Error:</b> Invalid email format. Must contain '@'.", parse_mode="HTML")
            return
        es_query = f'email:"{query_value}"'
        search_type = "email"

    elif command == '/pass':
        es_query = f'password:"{query_value}"'
        search_type = "password"

    log_search(user_id, message.from_user.first_name, search_type, query_value)

    params = {
        'q': es_query,
        'size': 100,
        'pretty': 'true'
    }

    start_time = time.time()
    try:
        response = requests.get(ES_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        # طباعة الخطأ في التيرمنال للمدير فقط
        print(f"Backend Error [Search]: {e}")
        # رسالة مبهمة وعامة للمستخدم
        bot.reply_to(message, "<b>Error:</b> Service is currently unavailable. Please try again later.", parse_mode="HTML")
        return

    end_time = time.time()
    search_duration = round(end_time - start_time, 4)

    hits_data = data.get('hits', {}).get('hits', [])
    total_results = len(hits_data)

    telegram_header = (
        "<blockquote>\n"
        f"<b>Time:</b> {search_duration}s\n"
        f"<b>Results:</b> {total_results}\n"
        "</blockquote>\n"
    )

    if total_results == 0:
        bot.reply_to(message, telegram_header + "No results found.", parse_mode="HTML")
        return

    formatted_message = ""
    file_content = f"Target: {query_value}\nTime: {search_duration}s\nResults: {total_results}\n\n"

    if command == '/email':
        formatted_message = f"<b>Email:</b> <code>{query_value}</code>\n<b>Passwords:</b>\n"
        file_content += f"Email: {query_value}\n\nPasswords:\n"

        passwords = set()
        for hit in hits_data:
            source = hit.get('_source', {})
            if 'password' in source:
                passwords.add(source['password'])

        formatted_message += "\n".join([f"<code>{p}</code>" for p in passwords])
        file_content += "\n".join(passwords)

    elif command == '/pass':
        formatted_message = f"<b>Password:</b> <code>{query_value}</code>\n<b>Emails:</b>\n"
        file_content += f"Password: {query_value}\n\nEmails:\n"

        emails = []
        for hit in hits_data:
            source = hit.get('_source', {})
            if 'email' in source:
                emails.append(source['email'])

        formatted_message += "\n".join([f"<code>{e}</code>" for e in emails])
        file_content += "\n".join(emails)

    if total_results <= 10:
        bot.reply_to(message, telegram_header + formatted_message, parse_mode="HTML")
    else:
        # إضافة طابع زمني للملف لمنع تداخل أسماء الملفات إذا بحث المستخدم مرتين بسرعة
        filename = f"search_{user_id}_{int(time.time())}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(file_content)

        with open(filename, "rb") as f:
            bot.send_document(
                message.chat.id, 
                f, 
                caption=telegram_header.strip(),
                parse_mode="HTML",
                reply_to_message_id=message.message_id
            )

        os.remove(filename)

print("Bot is running securely and multi-threaded...")
bot.infinity_polling()
