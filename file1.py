from telebot.async_telebot import AsyncTeleBot
import asyncio
import aiohttp
import json
import time
import os
import random
import threading

# ضع توكن البوت الخاص بك هنا
TOKEN = "7987425397:"

# ضع الـ ID الخاص بك هنا (مهم جداً للوحة التحكم)
ADMIN_ID = 77729359

# تم إزالة num_threads لأن البوت أصبح Async ولا يحتاج مسارات متعددة
bot = AsyncTeleBot(TOKEN)

ES_URL = "http://67.217.59.246:9200/matcher/_search"

last_search_times = {}
PERMISSIONS_FILE = "permissions.json"
file_lock = threading.Lock()

def load_permissions():
    """تحميل الصلاحيات من ملف الجيسون"""
    with file_lock:
        if not os.path.exists(PERMISSIONS_FILE):
            return {"allowed_users": [], "allowed_groups": []}
        try:
            with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"allowed_users": [], "allowed_groups": []}

def save_permissions(data):
    """حفظ الصلاحيات في ملف الجيسون"""
    with file_lock:
        with open(PERMISSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def is_allowed(message):
    """التحقق مما إذا كان المستخدم أو المجموعة لديهم صلاحية"""
    if message.from_user.id == ADMIN_ID:
        return True
        
    perms = load_permissions()
    
    if message.chat.type == 'private':
        return message.from_user.id in perms.get("allowed_users", [])
    else:
        # إذا كان في مجموعة، يجب أن تكون المجموعة مسموحة
        return message.chat.id in perms.get("allowed_groups", [])

# ================= لوحة تحكم الإدمن (مخفية للجميع عدا الإدمن) =================
@bot.message_handler(commands=['adduser', 'deluser', 'addgroup', 'delgroup', 'list'])
async def admin_controls(message):
    # تجاهل أي مستخدم عادي أو إذا كان الأمر في مجموعة
    if message.from_user.id != ADMIN_ID or message.chat.type != 'private':
        return

    command = message.text.split()[0]
    args = message.text.split()[1:]
    perms = load_permissions()

    if command == '/adduser':
        if not args:
            return await bot.reply_to(message, "<b>Usage:</b> <code>/adduser {User_ID}</code>", parse_mode="HTML")
        try:
            target_id = int(args[0])
            if target_id not in perms['allowed_users']:
                perms['allowed_users'].append(target_id)
                save_permissions(perms)
            await bot.reply_to(message, f"<b>Success:</b> User <code>{target_id}</code> has been granted private search access.", parse_mode="HTML")
        except ValueError:
            await bot.reply_to(message, "<b>Error:</b> Invalid ID format.", parse_mode="HTML")

    elif command == '/deluser':
        if not args:
            return await bot.reply_to(message, "<b>Usage:</b> <code>/deluser {User_ID}</code>", parse_mode="HTML")
        try:
            target_id = int(args[0])
            if target_id in perms['allowed_users']:
                perms['allowed_users'].remove(target_id)
                save_permissions(perms)
            await bot.reply_to(message, f"<b>Success:</b> User <code>{target_id}</code> access revoked.", parse_mode="HTML")
        except ValueError:
            await bot.reply_to(message, "<b>Error:</b> Invalid ID format.", parse_mode="HTML")

    elif command == '/addgroup':
        if not args:
            return await bot.reply_to(message, "<b>Usage:</b> <code>/addgroup {Group_ID}</code>", parse_mode="HTML")
        try:
            target_id = int(args[0])
            if target_id not in perms['allowed_groups']:
                perms['allowed_groups'].append(target_id)
                save_permissions(perms)
            await bot.reply_to(message, f"<b>Success:</b> Group <code>{target_id}</code> is now allowed.", parse_mode="HTML")
        except ValueError:
            await bot.reply_to(message, "<b>Error:</b> Invalid ID format.", parse_mode="HTML")

    elif command == '/delgroup':
        if not args:
            return await bot.reply_to(message, "<b>Usage:</b> <code>/delgroup {Group_ID}</code>", parse_mode="HTML")
        try:
            target_id = int(args[0])
            if target_id in perms['allowed_groups']:
                perms['allowed_groups'].remove(target_id)
                save_permissions(perms)
            await bot.reply_to(message, f"<b>Success:</b> Group <code>{target_id}</code> access revoked.", parse_mode="HTML")
        except ValueError:
            await bot.reply_to(message, "<b>Error:</b> Invalid ID format.", parse_mode="HTML")

    elif command == '/list':
        users = "\n".join([f"<code>{uid}</code>" for uid in perms.get('allowed_users', [])]) or "None"
        groups = "\n".join([f"<code>{gid}</code>" for gid in perms.get('allowed_groups', [])]) or "None"
        await bot.reply_to(message, f"<b>Allowed Users:</b>\n{users}\n\n<b>Allowed Groups:</b>\n{groups}", parse_mode="HTML")

# ================= أوامر البوت الأساسية =================
@bot.message_handler(commands=['start', 'help'])
async def send_instructions(message):
    # التحقق من الصلاحيات أولاً
    if not is_allowed(message):
        await bot.reply_to(message, "<b>Error:</b> You do not have permission to use the bot here.", parse_mode="HTML")
        return

    instructions = (
        "<b>Welcome.</b>\n\n"
        "<b>We have 4,606,063,150 emails</b>\n\n"
        "<b>Commands:</b>\n"
        "<b>/email {target}</b>\n"
        "<b>/pass {target}</b>\n"
        "<b>/random {count}</b>"
    )

    # إضافة لوحة التحكم فقط إذا كان المستلم هو الإدمن وفي الخاص
    if message.from_user.id == ADMIN_ID and message.chat.type == 'private':
        perms = load_permissions()
        u_count = len(perms.get('allowed_users', []))
        g_count = len(perms.get('allowed_groups', []))
        
        admin_panel = (
            "\n\n====================\n"
            "<b>🛠 ADMIN PANEL 🛠</b>\n"
            "====================\n"
            f"Allowed Users: {u_count}\n"
            f"Allowed Groups: {g_count}\n\n"
            "<b>Admin Commands:</b>\n"
            "<code>/adduser {ID}</code>\n"
            "<code>/deluser {ID}</code>\n"
            "<code>/addgroup {ID}</code>\n"
            "<code>/delgroup {ID}</code>\n"
            "<code>/list</code> - Show all IDs"
        )
        instructions += admin_panel

    await bot.reply_to(message, instructions, parse_mode="HTML")

@bot.message_handler(commands=['random'])
async def handle_random(message):
    if not is_allowed(message):
        await bot.reply_to(message, "<b>Error:</b> You do not have permission to search here.", parse_mode="HTML")
        return

    user_id = message.from_user.id
    current_time = time.time()

    if user_id in last_search_times and (current_time - last_search_times[user_id]) < 1:
        return
    last_search_times[user_id] = current_time

    try:
        count_str = message.text.split(" ", 1)[1].strip()
        count = int(count_str)
    except (IndexError, ValueError):
        await bot.reply_to(message, "<b>Error:</b> Invalid count. Use /random {Number}.", parse_mode="HTML")
        return

    if count > 149:
        await bot.reply_to(message, "<b>Error:</b> Maximum allowed count is 149.", parse_mode="HTML")
        return
    if count <= 0:
        return

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
        # استخدام aiohttp لجعل الاتصال بقاعدة البيانات سريع ولا يوقف البوت
        async with aiohttp.ClientSession() as session:
            async with session.get(ES_URL, params=params, timeout=15) as response:
                response.raise_for_status()
                data = await response.json()
    except Exception as e:
        print(f"Backend Error [Random]: {e}")
        await bot.reply_to(message, "<b>Error:</b> Service is currently unavailable. Please try again later.", parse_mode="HTML")
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
        await bot.reply_to(message, telegram_header + "No results found.", parse_mode="HTML")
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
        await bot.reply_to(message, telegram_header + formatted_message.strip(), parse_mode="HTML")
    else:
        filename = f"random_{user_id}_{int(time.time())}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(file_content.strip())

        with open(filename, "rb") as f:
            await bot.send_document(
                message.chat.id, 
                f, 
                caption=telegram_header.strip(),
                parse_mode="HTML",
                reply_to_message_id=message.message_id
            )

        os.remove(filename)

@bot.message_handler(commands=['email', 'pass'])
async def handle_search(message):
    if not is_allowed(message):
        await bot.reply_to(message, "<b>Error:</b> You do not have permission to search here.", parse_mode="HTML")
        return

    user_id = message.from_user.id
    current_time = time.time()

    if user_id in last_search_times and (current_time - last_search_times[user_id]) < 1:
        return

    last_search_times[user_id] = current_time

    command = message.text.split()[0]
    try:
        query_value = message.text.split(" ", 1)[1].strip()
    except IndexError:
        await bot.reply_to(message, "<b>Error:</b> Missing search parameter.", parse_mode="HTML")
        return

    if command == '/email':
        query_value = query_value.lower()
        if '@' not in query_value:
            await bot.reply_to(message, "<b>Error:</b> Invalid email format. Must contain '@'.", parse_mode="HTML")
            return
        es_query = f'email:"{query_value}"'

    elif command == '/pass':
        es_query = f'password:"{query_value}"'

    params = {
        'q': es_query,
        'size': 100,
        'pretty': 'true'
    }

    start_time = time.time()
    try:
        # استخدام aiohttp لجعل الاتصال بقاعدة البيانات سريع ولا يوقف البوت
        async with aiohttp.ClientSession() as session:
            async with session.get(ES_URL, params=params, timeout=15) as response:
                response.raise_for_status()
                data = await response.json()
    except Exception as e:
        print(f"Backend Error [Search]: {e}")
        await bot.reply_to(message, "<b>Error:</b> Service is currently unavailable. Please try again later.", parse_mode="HTML")
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
        await bot.reply_to(message, telegram_header + "No results found.", parse_mode="HTML")
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
        await bot.reply_to(message, telegram_header + formatted_message, parse_mode="HTML")
    else:
        filename = f"search_{user_id}_{int(time.time())}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(file_content)

        with open(filename, "rb") as f:
            await bot.send_document(
                message.chat.id, 
                f, 
                caption=telegram_header.strip(),
                parse_mode="HTML",
                reply_to_message_id=message.message_id
            )

        os.remove(filename)

print("Bot is running securely and fast (Async mode)...")
asyncio.run(bot.polling())
