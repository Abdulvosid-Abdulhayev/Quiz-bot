import telebot
from telebot import types
import datetime
import json
import os
import logging
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_TOKEN = os.getenv('API_TOKEN')
MAIN_ADMIN_ID = os.getenv('MAIN_ADMIN_ID')

# Logging configuration
logging.basicConfig(level=logging.DEBUG)

bot = telebot.TeleBot(API_TOKEN)

admins = {MAIN_ADMIN_ID}

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError:
        return {}

def save_json(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        logging.info(f"Data successfully saved to {filename}")
    except Exception as e:
        logging.error(f"Error saving data to {filename}: {e}")

# Load data from files
tests = load_json('test_data.json')
users = load_json('user.json')
address = load_json('address.json')
viloyatlar = list(address.keys())
required_channels = load_json('channels.json')

# Check if the user is an admin
def is_admin(chat_id):
    return str(chat_id) in admins

def generate_user_id():
    max_id = max([int(user['user_id']) for user in users.values()] or [0])
    return str(max_id + 1).zfill(5)

def is_valid_phone_number(phone):
    return re.fullmatch(r'^\+998\d{9}$', phone) is not None

def ensure_user_info(message):
    user_id = str(message.chat.id)
    if not check_channel_subscription(user_id):
        ask_to_join_channels(message)
        return
    if user_id not in users:
        users[user_id] = {
            'user_id': generate_user_id(),
            'tests': {},
            'tanga': 0
        }
    missing_fields = [field for field in ['name', 'age', 'phone', 'class', 'region', 'district'] if field not in users[user_id]]
    if missing_fields:
        request_user_info(message, missing_fields)
    else:
        show_user_main_menu(message)
    save_json('user.json', users)

def check_channel_subscription(user_id):
    for channel in required_channels:
        try:
            member = bot.get_chat_member(f"@{channel}", user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Error checking channel @{channel}: {e}")
            return False
    return True

def ask_to_join_channels(message):
    channels_links = "\n".join([f"@{channel}" for channel in required_channels])
    bot.send_message(
        message.chat.id,
        f"Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:\n\n{channels_links}\n\nBarcha kanallarga a'zo bo'lganingizdan so'ng, /start buyrug'ini kiriting."
    )

def request_user_info(message, fields):
    user_id = str(message.chat.id)
    field = fields[0]
    if field == 'name':
        msg = bot.send_message(message.chat.id, "Ismingizni kiriting:")
        bot.register_next_step_handler(msg, process_user_name, fields[1:])
    elif field == 'age':
        msg = bot.send_message(message.chat.id, "Yoshingizni kiriting (7-25 oralig'ida):")
        bot.register_next_step_handler(msg, process_user_age, fields[1:])
    elif field == 'phone':
        msg = bot.send_message(message.chat.id, "Telefon raqamingizni kiriting (+998XXXXXXXXX formatida):")
        bot.register_next_step_handler(msg, process_user_phone, fields[1:])
    elif field == 'class':
        msg = bot.send_message(message.chat.id, "Sinfingizni kiriting (1-12):")
        bot.register_next_step_handler(msg, process_user_class, fields[1:])
    elif field == 'region':
        markup = types.ReplyKeyboardMarkup(row_width=3)
        for region in viloyatlar:
            markup.add(types.KeyboardButton(region))
        back_button = types.KeyboardButton('⬅Ortga')
        markup.add(back_button)
        msg = bot.send_message(message.chat.id, "Viloyatingizni tanlang:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_user_region, fields[1:])
    elif field == 'district':
        region = users[user_id]['region']
        markup = types.ReplyKeyboardMarkup(row_width=3)
        for district in address[region]:
            markup.add(types.KeyboardButton(district))
        back_button = types.KeyboardButton('⬅Ortga')
        markup.add(back_button)
        msg = bot.send_message(message.chat.id, "Tumaningizni tanlang:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_user_district, fields[1:])

def process_user_name(message, fields):
    if message.text == '⬅Ortga':
        ensure_user_info(message)
        return
    user_id = str(message.chat.id)
    users[user_id]['name'] = message.text
    save_json('user.json', users)
    request_user_info(message, fields)

def process_user_age(message, fields):
    if message.text == '⬅Ortga':
        ensure_user_info(message)
        return
    try:
        age = int(message.text)
        if age < 7 or age > 25:
            msg = bot.send_message(message.chat.id, "Yosh 7 va 25 oralig'ida bo'lishi kerak. Iltimos, yoshingizni qaytadan kiriting:")
            bot.register_next_step_handler(msg, process_user_age, fields)
            return
        user_id = str(message.chat.id)
        users[user_id]['age'] = age
        save_json('user.json', users)
        request_user_info(message, fields)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Iltimos, to'g'ri yoshni kiriting:")
        bot.register_next_step_handler(msg, process_user_age, fields)
        return

def process_user_phone(message, fields):
    if message.text == '⬅Ortga':
        ensure_user_info(message)
        return
    phone = message.text
    if not is_valid_phone_number(phone):
        msg = bot.send_message(message.chat.id, "Iltimos, telefon raqamingizni +998XXXXXXXXX formatida kiriting:")
        bot.register_next_step_handler(msg, process_user_phone, fields)
        return
    user_id = str(message.chat.id)
    users[user_id]['phone'] = phone
    save_json('user.json', users)
    request_user_info(message, fields)

def process_user_class(message, fields):
    if message.text == '⬅Ortga':
        ensure_user_info(message)
        return
    try:
        class_id = int(message.text)
        if class_id < 1 or class_id > 12:
            msg = bot.send_message(message.chat.id, "Sinf 1 va 12 oralig'ida bo'lishi kerak. Iltimos, sinfni qaytadan kiriting:")
            bot.register_next_step_handler(msg, process_user_class, fields)
            return
        user_id = str(message.chat.id)
        users[user_id]['class'] = class_id
        save_json('user.json', users)
        request_user_info(message, fields)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Iltimos, to'g'ri sinf raqamini kiriting:")
        bot.register_next_step_handler(msg, process_user_class, fields)
        return

def process_user_region(message, fields):
    if message.text == '⬅Ortga':
        ensure_user_info(message)
        return
    user_id = str(message.chat.id)
    region = message.text
    if region not in viloyatlar:
        msg = bot.send_message(message.chat.id, "Noto'g'ri viloyat. Iltimos, qaytadan tanlang:")
        bot.register_next_step_handler(msg, process_user_region, fields)
        return
    users[user_id]['region'] = region
    save_json('user.json', users)
    request_user_info(message, fields)

def process_user_district(message, fields):
    if message.text == '⬅Ortga':
        ensure_user_info(message)
        return
    user_id = str(message.chat.id)
    district = message.text
    if 'tuman' not in district.lower():
        district += ' tuman'
    if district not in address[users[user_id]['region']]:
        msg = bot.send_message(message.chat.id, "Noto'g'ri tuman. Iltimos, qaytadan tanlang:")
        bot.register_next_step_handler(msg, process_user_district, fields)
        return
    users[user_id]['district'] = district
    save_json('user.json', users)
    ensure_user_info(message)

# Admin panel
def admin_panel(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    markup = types.ReplyKeyboardMarkup(row_width=2)
    test_upload = types.KeyboardButton('📄 Test yuklash')
    view_results = types.KeyboardButton('📊 Natijalarni ko\'rish')
    view_users = types.KeyboardButton('👥 Foydalanuvchilar ko\'rish')
    manage_admins = types.KeyboardButton('🔧 Adminlar')
    manage_channels = types.KeyboardButton('📺 Kanallarni boshqarish')
    give_tanga = types.KeyboardButton('💰 Tangalar berish')
    broadcast_message = types.KeyboardButton('📢 Barchaga xabar yuborish')
    markup.add(test_upload, view_results, view_users, manage_admins, manage_channels, give_tanga, broadcast_message)
    bot.send_message(message.chat.id, "Admin paneliga xush kelibsiz!", reply_markup=markup)

def back_to_admin_main(message):
    if not is_admin(message.chat.id):
        ensure_user_info(message)
        return

    markup = types.ReplyKeyboardMarkup(row_width=2)
    test_upload = types.KeyboardButton('📄 Test yuklash')
    view_results = types.KeyboardButton('📊 Natijalarni ko\'rish')
    view_users = types.KeyboardButton('👥 Foydalanuvchilar ko\'rish')
    manage_admins = types.KeyboardButton('🔧 Adminlar')
    manage_channels = types.KeyboardButton('📺 Kanallarni boshqarish')
    give_tanga = types.KeyboardButton('💰 Tangalar berish')
    broadcast_message = types.KeyboardButton('📢 Barchaga xabar yuborish')
    markup.add(test_upload, view_results, view_users, manage_admins, manage_channels, give_tanga, broadcast_message)

    bot.send_message(message.chat.id, "Admin panelining asosiy menyusiga qaytdingiz!", reply_markup=markup)

def upload_test(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    markup = types.ReplyKeyboardMarkup(row_width=2)
    back_button = types.KeyboardButton('⬅Ortga')
    markup.add(back_button)
    
    msg = bot.send_message(message.chat.id, "Iltimos, sinfni kiriting (masalan, 9):", reply_markup=markup)
    bot.register_next_step_handler(msg, process_class_step)

def process_class_step(message):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    try:
        class_id = int(message.text)
        if class_id < 1 or class_id > 12:
            msg = bot.send_message(message.chat.id, "Sinf 1 va 12 oralig'ida bo'lishi kerak. Iltimos, sinfni qaytadan kiriting:")
            bot.register_next_step_handler(msg, process_class_step)
            return
        if class_id not in tests:
            tests[class_id] = {}
        msg = bot.send_message(message.chat.id, "Endi test ID kiritishingiz kerak:")
        bot.register_next_step_handler(msg, process_test_id_step, class_id)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Iltimos, to'g'ri sinf raqamini kiriting:")
        bot.register_next_step_handler(msg, process_class_step)
        return

def process_test_id_step(message, class_id):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    
    test_id = message.text
    
    if test_id in tests.get(class_id, {}):
        msg = bot.send_message(message.chat.id, "Bu test ID allaqachon mavjud. Iltimos, boshqa test ID kiritishingiz kerak:")
        bot.register_next_step_handler(msg, process_test_id_step, class_id)
        return
    
    if class_id not in tests:
        tests[class_id] = {}
    
    tests[class_id][test_id] = {'test_id': test_id, 'questions': []}
    
    markup = types.ReplyKeyboardMarkup(row_width=2)
    back_button = types.KeyboardButton('⬅Ortga')
    markup.add(back_button)

    msg = bot.send_message(message.chat.id, "Testning boshlanish vaqtini kiriting (YYYY-MM-DD HH:MM):", reply_markup=markup)
    bot.register_next_step_handler(msg, process_start_time_step, class_id, test_id)

def process_start_time_step(message, class_id, test_id):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    start_time = message.text
    try:
        start_datetime = datetime.datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        tests[class_id][test_id]['start_time'] = start_time
        markup = types.ReplyKeyboardMarkup(row_width=2)
        back_button = types.KeyboardButton('⬅Ortga')
        markup.add(back_button)
        msg = bot.send_message(message.chat.id, "Testning tugash vaqtini kiriting (YYYY-MM-DD HH:MM):", reply_markup=markup)
        bot.register_next_step_handler(msg, process_end_time_step, class_id, test_id, start_datetime)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Vaqt formati noto'g'ri. Iltimos, boshlanish vaqtini qaytadan kiriting (YYYY-MM-DD HH:MM):")
        bot.register_next_step_handler(msg, process_start_time_step, class_id, test_id)
        return

def process_end_time_step(message, class_id, test_id, start_datetime):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    end_time = message.text
    try:
        end_datetime = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M')
        if end_datetime <= start_datetime:
            msg = bot.send_message(message.chat.id, "Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak. Iltimos, tugash vaqtini qaytadan kiriting (YYYY-MM-DD HH:MM):")
            bot.register_next_step_handler(msg, process_end_time_step, class_id, test_id, start_datetime)
            return
        
        tests[class_id][test_id]['end_time'] = end_time
        
        markup = types.ReplyKeyboardMarkup(row_width=2)
        back_button = types.KeyboardButton('⬅Ortga')
        finish_button = types.KeyboardButton('✅ Yakunlash')
        markup.add(back_button, finish_button)
        msg = bot.send_message(message.chat.id, "Endi test savolini kiriting:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_question_step, class_id, test_id)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Vaqt formati noto'g'ri. Iltimos, tugash vaqtini qaytadan kiriting (YYYY-MM-DD HH:MM):")
        bot.register_next_step_handler(msg, process_end_time_step, class_id, test_id, start_datetime)
        return

def process_question_step(message, class_id, test_id):
    if message.text == '✅ Yakunlash':
        save_json('test_data.json', tests)
        bot.send_message(message.chat.id, "Test muvaffaqiyatli saqlandi va yakunlandi!")
        back_to_admin_main(message)
        return

    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return

    question_text = message.text
    msg = bot.send_message(message.chat.id, "Variantlar sonini kiriting:")
    bot.register_next_step_handler(msg, process_option_count_step, class_id, test_id, question_text)

def process_option_count_step(message, class_id, test_id, question_text):
    if message.text == '✅ Yakunlash':
        save_json('test_data.json', tests)
        bot.send_message(message.chat.id, "Test muvaffaqiyatli saqlandi va yakunlandi!")
        back_to_admin_main(message)
        return

    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return

    try:
        option_count = int(message.text)
        if option_count < 2:
            msg = bot.send_message(message.chat.id, "Iltimos, kamida 2 ta variant kiriting:")
            bot.register_next_step_handler(msg, process_option_count_step, class_id, test_id, question_text)
            return

        questions = tests[class_id][test_id]['questions']
        questions.append({'question': question_text, 'option_count': option_count})

        markup = types.ReplyKeyboardMarkup(row_width=2)
        for idx in range(option_count):
            markup.add(types.KeyboardButton(chr(65 + idx)))
        msg = bot.send_message(message.chat.id, "To'g'ri javobni tanlang:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_correct_answer_step, class_id, test_id, question_text, option_count)

    except ValueError:
        msg = bot.send_message(message.chat.id, "Iltimos, raqam kiriting:")
        bot.register_next_step_handler(msg, process_option_count_step, class_id, test_id, question_text)
        return

def process_correct_answer_step(message, class_id, test_id, question_text, option_count):
    correct_answer = message.text.strip().upper()
    
    questions = tests[class_id][test_id]['questions']
    questions[-1]['correct_answer'] = correct_answer
    
    markup = types.ReplyKeyboardMarkup(row_width=2)
    back_button = types.KeyboardButton('⬅Ortga')
    finish_button = types.KeyboardButton('✅ Yakunlash')
    markup.add(back_button, finish_button)
    msg = bot.send_message(message.chat.id, "Yangi savolni kiriting yoki '✅ Yakunlash' tugmasini bosing:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_question_step, class_id, test_id)

def manage_admins(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    markup = types.ReplyKeyboardMarkup(row_width=2)
    add_admin = types.KeyboardButton('Yangi admin qo\'shish')
    remove_admin = types.KeyboardButton('Adminni o\'chirish')
    view_admins = types.KeyboardButton('Adminlar ro\'yxati')
    back_button = types.KeyboardButton('⬅Ortga')
    markup.add(add_admin, remove_admin, view_admins, back_button)
    bot.send_message(message.chat.id, "Adminlarni boshqarish paneli:", reply_markup=markup)

def add_admin_step(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    msg = bot.send_message(message.chat.id, "Yangi adminning chat ID sini kiriting:")
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(message):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    new_admin_id = message.text
    if not new_admin_id.isdigit():
        bot.send_message(message.chat.id, "Chat ID faqat raqamlardan iborat bo'lishi kerak.")
        return
    if new_admin_id not in users:
        bot.send_message(message.chat.id, "Chat ID mavjud foydalanuvchi emas.")
        return
    if new_admin_id not in admins:
        admins.add(new_admin_id)
        bot.send_message(message.chat.id, f"Chat ID {new_admin_id} admin qilib qo'shildi.")
    else:
        bot.send_message(message.chat.id, f"Chat ID {new_admin_id} allaqachon admin.")
    save_json('user.json', users)

def remove_admin_step(message):
    if not is_admin(message.chat.id) or str(message.chat.id) != MAIN_ADMIN_ID:
        bot.send_message(message.chat.id, "Sizda bu amalni bajarish uchun ruxsat yo'q.")
        return
    
    msg = bot.send_message(message.chat.id, "Adminni o'chirish uchun chat ID sini kiriting:")
    bot.register_next_step_handler(msg, process_remove_admin)

def process_remove_admin(message):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    remove_admin_id = message.text
    if remove_admin_id in admins:
        admins.remove(remove_admin_id)
        bot.send_message(message.chat.id, f"Chat ID {remove_admin_id} adminlardan o'chirildi.")
    else:
        bot.send_message(message.chat.id, f"Chat ID {remove_admin_id} admin emas.")
    save_json('user.json', users)

def view_admins_list(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    admin_list = "Adminlar ro'yxati:\n" + "\n".join(admins)
    bot.send_message(message.chat.id, admin_list)

def show_user_main_menu(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    test_start = types.KeyboardButton('📄 Test boshlash')
    view_results = types.KeyboardButton('📊 Natijalarni ko\'rish')
    view_info = types.KeyboardButton('👤 Ma\'lumotlarni ko\'rish')
    edit_info = types.KeyboardButton('✏ Ma\'lumotlarni o\'zgartirish')
    view_tanga = types.KeyboardButton('💰 Sandiq')
    markup.add(test_start, view_results, view_info, edit_info, view_tanga)
    bot.send_message(message.chat.id, f"Xush kelibsiz, {users[str(message.chat.id)]['name']}!", reply_markup=markup)

def start_test(message):
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    msg = bot.send_message(message.chat.id, "Iltimos, test ID kiritishingiz kerak:")
    bot.register_next_step_handler(msg, process_test_id)

def process_test_id(message):
    if message.text == '⬅Ortga':
        show_user_main_menu(message)
        return
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    test_id = message.text
    user_id = str(message.chat.id)

    if test_id in users[user_id]['tests'] and not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Siz ushbu testni allaqachon yechib bo'lgansiz.")
        return
    
    for class_id, class_tests in tests.items():
        if test_id in class_tests:
            test_data = class_tests[test_id]
            now = datetime.datetime.now()
            start_time = datetime.datetime.strptime(test_data['start_time'], '%Y-%m-%d %H:%M')
            end_time = datetime.datetime.strptime(test_data['end_time'], '%Y-%m-%d %H:%M')
            if now < start_time:
                bot.send_message(message.chat.id, "Test hali boshlanmagan.")
                return
            elif now > end_time:
                bot.send_message(message.chat.id, "Test tugagan.")
                return
            users[user_id]['tests'][test_id] = {'answers': [], 'score': 0}
            save_json('user.json', users)
            ask_question(message, class_id, test_id, 0)
            return
    bot.send_message(message.chat.id, "Test topilmadi.")

def ask_question(message, class_id, test_id, question_index):
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    if question_index < len(tests[class_id][test_id]['questions']):
        question_data = tests[class_id][test_id]['questions'][question_index]
        question_text = question_data['question']
        option_count = question_data['option_count']
        markup = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True)
        for idx in range(option_count):
            markup.add(types.KeyboardButton(chr(65 + idx)))
        msg = bot.send_message(message.chat.id, question_text, reply_markup=markup)
        bot.register_next_step_handler(msg, process_answer, class_id, test_id, question_index)
    else:
        calculate_score(message, class_id, test_id)

def process_answer(message, class_id, test_id, question_index):
    if message.text == '⬅Ortga':
        show_user_main_menu(message)
        return
    user_id = str(message.chat.id)
    selected_option = message.text.strip().upper()
    
    users[user_id]['tests'][test_id]['answers'].append(selected_option)
    
    save_json('user.json', users)
    ask_question(message, class_id, test_id, question_index + 1)

def calculate_score(message, class_id, test_id):
    user_id = str(message.chat.id)
    user_answers = users[user_id]['tests'][test_id]['answers']
    questions = tests[class_id][test_id]['questions']
    
    score = sum(1 for user_answer, question in zip(user_answers, questions) if user_answer == question.get('correct_answer'))
    
    users[user_id]['tests'][test_id]['score'] = score
    save_json('user.json', users)
    
    bot.send_message(message.chat.id, f"Test yakunlandi! Sizning balingiz: {score}")
    
    calculate_rewards(user_id, score, len(questions))
    show_user_main_menu(message)

def calculate_rewards(user_id, score, total_questions):
    percentage = (score / total_questions) * 100
    rewards = 0
    if percentage > 90:
        rewards += 10
    elif percentage > 85:
        rewards += 9
    elif percentage > 80:
        rewards += 8
    elif percentage > 70:
        rewards += 7
    elif percentage > 65:
        rewards += 6
    elif percentage > 50:
        rewards += 5
    elif percentage > 30:
        rewards += 3
    elif percentage > 0:
        rewards += 1
    if score == 0:
        rewards -= 5
    users[user_id]['tanga'] += rewards
    save_json('user.json', users)

def view_results(message):
    markup = types.ReplyKeyboardMarkup(row_width=1)
    back = types.KeyboardButton("⬅Ortga") 
    markup.add(back)
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    if is_admin(message.chat.id):
        markup.add(types.KeyboardButton("Chat ID bilan"), types.KeyboardButton("Chat ID siz"))
        msg = bot.send_message(message.chat.id, "Natijalarni ko'rish usulini tanlang:", reply_markup=markup)
        bot.register_next_step_handler(msg, select_result_type)
    else:
        msg = bot.send_message(message.chat.id, "Iltimos, test ID kiritishingiz kerak:", reply_markup=markup)
        bot.register_next_step_handler(msg, show_user_results)

def select_result_type(message):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    if message.text == "Chat ID bilan":
        msg = bot.send_message(message.chat.id, "Iltimos, test ID kiritishingiz kerak:")
        bot.register_next_step_handler(msg, lambda msg: show_admin_results(msg, with_chat_id=True))
    elif message.text == "Chat ID siz":
        msg = bot.send_message(message.chat.id, "Iltimos, test ID kiritishingiz kerak:")
        bot.register_next_step_handler(msg, lambda msg: show_admin_results(msg, with_chat_id=False))
    else:
        bot.send_message(message.chat.id, "Noto'g'ri tanlov. Iltimos, qaytadan tanlang.")
        view_results(message)

def show_admin_results(message, with_chat_id):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    test_id = message.text
    user_scores = [
        (users[uid]['name'], users[uid]['tests'][test_id]['score'], uid) 
        for uid in users if test_id in users[uid]['tests']
    ]
    user_scores.sort(key=lambda x: x[1], reverse=True)
    
    if with_chat_id:
        results = "\n".join([f"Ism: {name}, Baho: {score}, Chat ID: {uid}" for name, score, uid in user_scores])
    else:
        results = "\n".join([f"Ism: {name}, Baho: {score}" for name, score, _ in user_scores])
    
    bot.send_message(message.chat.id, f"Test ID: {test_id}\nNatijalar:\n{results}")


def show_user_results(message):
    if message.text == '⬅Ortga':
        show_user_main_menu(message)
        return
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    test_id = message.text
    user_id = str(message.chat.id)
    if test_id in users[user_id]['tests']:
        score = users[user_id]['tests'][test_id]['score']
        user_scores = [users[uid]['tests'][test_id]['score'] for uid in users if test_id in users[uid]['tests']]
        user_scores.sort(reverse=True)
        rank = user_scores.index(score) + 1
        bot.send_message(message.chat.id, f"Test ID: {test_id}\nSizning balingiz: {score}\nO'rningiz: {rank}/{len(user_scores)}")
        send_rankings(message.chat.id, test_id)
    else:
        bot.send_message(message.chat.id, "Siz bunday testga qatnashmagansiz.")


def view_information(message):
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    user_id = str(message.chat.id)
    user_info = f"Ismingiz: {users[user_id]['name']}\nYoshingiz: {users[user_id]['age']}\nTelefon raqamingiz: {users[user_id]['phone']}\nSinfingiz: {users[user_id]['class']}\nViloyat: {users[user_id]['region']}\nTuman: {users[user_id]['district']}\nFoydalanuvchi ID: {users[user_id]['user_id']}\nTanga: {users[user_id]['tanga']}"
    bot.send_message(message.chat.id, user_info)

def edit_information(message):
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    markup = types.ReplyKeyboardMarkup(row_width=2)
    edit_name = types.KeyboardButton('Ismni o\'zgartirish')
    edit_region = types.KeyboardButton('Viloyatni o\'zgartirish')
    edit_district = types.KeyboardButton('Tumanini o\'zgartirish')
    back_button = types.KeyboardButton('⬅Ortga')
    markup.add(edit_name, edit_region, edit_district, back_button)
    bot.send_message(message.chat.id, "Qaysi ma'lumotni o'zgartirmoqchisiz?", reply_markup=markup)

def change_information_step(message):
    if message.text == '⬅Ortga':
        show_user_main_menu(message)
    elif message.text == 'Ismni o\'zgartirish':
        msg = bot.send_message(message.chat.id, "Yangi ismingizni kiriting:")
        bot.register_next_step_handler(msg, update_name)
    elif message.text == 'Viloyatni o\'zgartirish':
        markup = types.ReplyKeyboardMarkup(row_width=3)
        for region in viloyatlar:
            markup.add(types.KeyboardButton(region))
        back_button = types.KeyboardButton('⬅Ortga')
        markup.add(back_button)
        msg = bot.send_message(message.chat.id, "Yangi viloyatingizni tanlang:", reply_markup=markup)
        bot.register_next_step_handler(msg, update_region)
    elif message.text == 'Tumanini o\'zgartirish':
        region = users[str(message.chat.id)]['region']
        markup = types.ReplyKeyboardMarkup(row_width=3)
        for district in address[region]:
            markup.add(types.KeyboardButton(district))
        back_button = types.KeyboardButton('⬅Ortga')
        markup.add(back_button)
        msg = bot.send_message(message.chat.id, "Yangi tumaningizni tanlang:", reply_markup=markup)
        bot.register_next_step_handler(msg, update_district)

def update_name(message):
    user_id = str(message.chat.id)
    new_name = message.text
    users[user_id]['name'] = new_name
    save_json('user.json', users)
    bot.send_message(message.chat.id, f"Ismingiz muvaffaqiyatli yangilandi: {new_name}")
    show_user_main_menu(message)

def update_region(message):
    user_id = str(message.chat.id)
    selected_region = message.text
    if selected_region not in viloyatlar:
        msg = bot.send_message(message.chat.id, "Noto'g'ri viloyat. Iltimos, qaytadan tanlang:")
        bot.register_next_step_handler(msg, update_region)
        return
    users[user_id]['region'] = selected_region
    users[user_id].pop('district', None)
    save_json('user.json', users)
    bot.send_message(message.chat.id, f"Viloyatingiz muvaffaqiyatli yangilandi: {selected_region}")
    markup = types.ReplyKeyboardMarkup(row_width=3)
    for district in address[selected_region]:
        markup.add(types.KeyboardButton(district))
    back_button = types.KeyboardButton('⬅Ortga')
    markup.add(back_button)
    msg = bot.send_message(message.chat.id, "Endi yangi tumaningizni tanlang:", reply_markup=markup)
    bot.register_next_step_handler(msg, update_district)

def update_district(message):
    user_id = str(message.chat.id)
    selected_district = message.text
    if 'tuman' not in selected_district.lower():
        selected_district += ' tuman'
    if selected_district not in address[users[user_id]['region']]:
        msg = bot.send_message(message.chat.id, "Noto'g'ri tuman. Iltimos, qaytadan tanlang:")
        bot.register.next_step_handler(msg, update_district)
        return
    users[user_id]['district'] = selected_district
    save_json('user.json', users)
    bot.send_message(message.chat.id, f"Tumaningiz muvaffaqiyatli yangilandi: {selected_district}")
    show_user_main_menu(message)

def view_users(message):
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    markup = types.ReplyKeyboardMarkup(row_width=3, one_time_keyboard=True)
    for i in range(1, 13):
        markup.add(types.KeyboardButton(f"{i} sinf"))
    back_button = types.KeyboardButton('⬅Ortga')
    markup.add(back_button)
    msg = bot.send_message(message.chat.id, "Sinfni tanlang:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_user_view_class)

def process_user_view_class(message):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return

    selected_class = message.text.split()[0]
    if not selected_class.isdigit():
        bot.send_message(message.chat.id, "Noto'g'ri sinf tanlandi. Iltimos, qayta tanlang.")
        view_users(message)
        return

    markup = types.ReplyKeyboardMarkup(row_width=3, one_time_keyboard=True)
    for region in viloyatlar:
        markup.add(types.KeyboardButton(region))
    back_button = types.KeyboardButton('⬅Ortga')
    markup.add(back_button)
    msg = bot.send_message(message.chat.id, "Viloyatni tanlang:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_user_view_region, selected_class)

def process_user_view_region(message, selected_class):
    if message.text == '⬅Ortga':
        view_users(message)
        return

    selected_region = message.text
    if selected_region not in viloyatlar:
        bot.send_message(message.chat.id, "Noto'g'ri viloyat tanlandi. Iltimos, qayta tanlang.")
        process_user_view_class(message)
        return

    markup = types.ReplyKeyboardMarkup(row_width=3, one_time_keyboard=True)
    for district in address[selected_region]:
        markup.add(types.KeyboardButton(district))
    back_button = types.KeyboardButton('⬅Ortga')
    markup.add(back_button)
    msg = bot.send_message(message.chat.id, "Tumaningizni tanlang:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_user_view_district, selected_class, selected_region)

def process_user_view_district(message, selected_class, selected_region):
    if message.text == '⬅Ortga':
        process_user_view_region(message, selected_class)
        return

    selected_district = message.text
    if 'tuman' not in selected_district.lower():
        selected_district += ' tuman'

    if selected_district not in address[selected_region]:
        bot.send_message(message.chat.id, "Noto'g'ri tuman tanlandi. Iltimos, qayta tanlang.")
        process_user_view_region(message, selected_class)
        return

    user_list = [user for user in users.values() if user.get('class') == int(selected_class) and user.get('region') == selected_region and user.get('district') == selected_district]
    
    if user_list:
        user_info = "\n\n".join([f"Ism: {user['name']}\nYosh: {user['age']}\nTelefon: {user['phone']}\nSinf: {user['class']}\nViloyat: {user['region']}\nTuman: {user['district']}\nFoydalanuvchi ID: {user['user_id']}\nTanga: {user['tanga']}" for user in user_list])
        bot.send_message(message.chat.id, f"Foydalanuvchilar ro'yxati:\n\n{user_info}")
    else:
        bot.send_message(message.chat.id, "Bu tanlov bo'yicha foydalanuvchilar topilmadi.")

    back_to_admin_main(message)

def view_tanga(message):
    if not check_channel_subscription(message.chat.id):
        ask_to_join_channels(message)
        return
    user_id = str(message.chat.id)
    tanga = users[user_id]['tanga']
    bot.send_message(message.chat.id, f"Sizning tangalaringiz soni: {tanga}")

def handle_give_tanga(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    msg = bot.send_message(message.chat.id, "Foydalanuvchi ID sini kiriting:")
    bot.register_next_step_handler(msg, process_user_id_for_tanga)

def process_user_id_for_tanga(message):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return

    user_id = message.text.strip()
    if user_id not in users:
        bot.send_message(message.chat.id, "Foydalanuvchi topilmadi. Iltimos, to'g'ri foydalanuvchi ID sini kiriting.")
        return
    
    msg = bot.send_message(message.chat.id, f"Qancha tanga berishni xohlaysiz {users[user_id]['name']} foydalanuvchisiga?")
    bot.register_next_step_handler(msg, process_tanga_amount, user_id)

def process_tanga_amount(message, user_id):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return

    try:
        tanga_amount = int(message.text.strip())
        
        users[user_id]['tanga'] += tanga_amount
        save_json('user.json', users)
        bot.send_message(message.chat.id, f"{users[user_id]['name']} foydalanuvchisiga {tanga_amount} tanga berildi.")
    except ValueError:
        bot.send_message(message.chat.id, "Iltimos, raqam kiriting.")
        msg = bot.send_message(message.chat.id, f"Qancha tanga berishni xohlaysiz {users[user_id]['name']} foydalanuvchisiga?")
        bot.register_next_step_handler(msg, process_tanga_amount, user_id)
        return

    back_to_admin_main(message)

def send_rankings(chat_id, test_id):
    user_scores = [(uid, users[uid]['name'], users[uid]['tests'][test_id]['score']) for uid in users if test_id in users[uid]['tests']]
    user_scores.sort(key=lambda x: x[2], reverse=True)
    top_10 = user_scores[:10]
    user_id = str(chat_id)
    user_rank = next((rank + 1 for rank, (uid, _, _) in enumerate(user_scores) if uid == user_id), None)
    rankings = "Top 10:\n"
    for rank, (uid, name, score) in enumerate(top_10, start=1):
        rankings += f"{rank}. {name} - {score} ball\n"
    if user_rank and user_rank > 10:
        rankings += "...\n"
        user_score = next(score for uid, name, score in user_scores if uid == user_id)
        rankings += f"{user_rank}. {users[user_id]['name']} - {user_score} ball\n"
    bot.send_message(chat_id, f"Test ID: {test_id}\nNatijalar:\n{rankings}")

def manage_channels(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    markup = types.ReplyKeyboardMarkup(row_width=2)
    add_channel = types.KeyboardButton('Kanal qo\'shish')
    remove_channel = types.KeyboardButton('Kanalni o\'chirish')
    view_channels = types.KeyboardButton('Kanallar ro\'yxati')
    back_button = types.KeyboardButton('⬅Ortga')
    markup.add(add_channel, remove_channel, view_channels, back_button)
    bot.send_message(message.chat.id, "Kanallarni boshqarish paneli:", reply_markup=markup)

def add_channel_step(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    msg = bot.send_message(message.chat.id, "Qo'shmoqchi bo'lgan kanalni username'ini kiriting (masalan, channel_name):")
    bot.register_next_step_handler(msg, process_add_channel)

def process_add_channel(message):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    
    channel_username = message.text.strip().replace("@", "")
    if channel_username not in required_channels:
        required_channels.append(channel_username)
        save_json('channels.json', required_channels)
        bot.send_message(message.chat.id, f"Kanal @{channel_username} muvaffaqiyatli qo'shildi.")
    else:
        bot.send_message(message.chat.id, f"Kanal @{channel_username} allaqachon mavjud.")
    back_to_admin_main(message)

def remove_channel_step(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    msg = bot.send_message(message.chat.id, "O'chirmoqchi bo'lgan kanalni username'ini kiriting (masalan, channel_name):")
    bot.register_next_step_handler(msg, process_remove_channel)

def process_remove_channel(message):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    
    channel_username = message.text.strip().replace("@", "")
    if channel_username in required_channels:
        required_channels.remove(channel_username)
        save_json('channels.json', required_channels)
        bot.send_message(message.chat.id, f"Kanal @{channel_username} muvaffaqiyatli o'chirildi.")
    else:
        bot.send_message(message.chat.id, f"Kanal @{channel_username} topilmadi.")
    back_to_admin_main(message)

def view_channels_list(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    if required_channels:
        channels_list = "\n".join([f"@{channel}" for channel in required_channels])
        bot.send_message(message.chat.id, f"Kanallar ro'yxati:\n\n{channels_list}")
    else:
        bot.send_message(message.chat.id, "Hozircha hech qanday kanal qo'shilmagan.")
    back_to_admin_main(message)

def broadcast_message(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "Sizda admin huquqlari yo'q.")
        return
    
    msg = bot.send_message(message.chat.id, "Yuboriladigan xabarni kiriting:")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    if message.text == '⬅Ortga':
        back_to_admin_main(message)
        return
    
    text = message.text
    for user_id in users:
        try:
            bot.send_message(user_id, text)
        except Exception as e:
            logging.error(f"Xabar yuborishda xatolik: {e}")
    bot.send_message(message.chat.id, "Xabar barcha foydalanuvchilarga yuborildi.")
    back_to_admin_main(message)

@bot.message_handler(commands=['start'])
def handle_start(message):
    ensure_user_info(message)

@bot.message_handler(commands=['admin_start'])
def handle_admin_start(message):
    admin_panel(message)

@bot.message_handler(func=lambda message: message.text == '📺 Kanallarni boshqarish')
def handle_manage_channels(message):
    manage_channels(message)

@bot.message_handler(func=lambda message: message.text == 'Kanal qo\'shish')
def handle_add_channel(message):
    add_channel_step(message)

@bot.message_handler(func=lambda message: message.text == 'Kanalni o\'chirish')
def handle_remove_channel(message):
    remove_channel_step(message)

@bot.message_handler(func=lambda message: message.text == 'Kanallar ro\'yxati')
def handle_view_channels(message):
    view_channels_list(message)

@bot.message_handler(func=lambda message: message.text == '⬅Ortga')
def handle_back(message):
    if is_admin(message.chat.id):
        back_to_admin_main(message)
    else:
        show_user_main_menu(message)

@bot.message_handler(func=lambda message: message.text == '👤 Ma\'lumotlarni ko\'rish')
def handle_view_information(message):
    view_information(message)

@bot.message_handler(func=lambda message: message.text == '✏ Ma\'lumotlarni o\'zgartirish')
def handle_edit_information(message):
    edit_information(message)

@bot.message_handler(func=lambda message: message.text == '📄 Test boshlash')
def handle_start_test(message):
    start_test(message)

@bot.message_handler(func=lambda message: message.text == '📊 Natijalarni ko\'rish')
def handle_view_results(message):
    view_results(message)

@bot.message_handler(func=lambda message: message.text == '💰 Sandiq')
def handle_view_tanga(message):
    view_tanga(message)

@bot.message_handler(func=lambda message: message.text == '📄 Test yuklash')
def handle_test_upload(message):
    upload_test(message)

@bot.message_handler(func=lambda message: message.text == '🔧 Adminlar')
def handle_manage_admins(message):
    manage_admins(message)

@bot.message_handler(func=lambda message: message.text == 'Yangi admin qo\'shish')
def handle_add_admin_step(message):
    add_admin_step(message)

@bot.message_handler(func=lambda message: message.text == 'Adminni o\'chirish')
def handle_remove_admin_step(message):
    remove_admin_step(message)

@bot.message_handler(func=lambda message: message.text == 'Adminlar ro\'yxati')
def handle_view_admins_list(message):
    view_admins_list(message)

@bot.message_handler(func=lambda message: message.text == 'Ismni o\'zgartirish')
def handle_change_name(message):
    change_information_step(message)

@bot.message_handler(func=lambda message: message.text == 'Viloyatni o\'zgartirish')
def handle_change_region(message):
    change_information_step(message)

@bot.message_handler(func=lambda message: message.text == 'Tumanini o\'zgartirish')
def handle_change_district(message):
    change_information_step(message)

@bot.message_handler(func=lambda message: message.text == '👥 Foydalanuvchilar ko\'rish')
def handle_view_users(message):
    view_users(message)

@bot.message_handler(func=lambda message: message.text == '💰 Tangalar berish')
def handle_give_tanga_button(message):
    handle_give_tanga(message)

@bot.message_handler(func=lambda message: message.text == '📢 Barchaga xabar yuborish')
def handle_broadcast_message(message):
    broadcast_message(message)

# Start the bot
bot.infinity_polling(none_stop=True)
