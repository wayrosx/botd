import logging
import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ⚠️ ЗАМЕНИТЕ ЭТОТ ТОКЕН НА ВАШ РЕАЛЬНЫЙ ТОКЕН БОТА ⚠️
BOT_TOKEN = "8417399077:AAFW3-iel7rGYRwA6ORdbr9V036hKFA18L8"

# ⚠️ ЗАМЕНИТЕ НА ВАШ USER_ID ⚠️
ADMIN_IDS = [1292233190, 7805404869, 7691643567]

# Состояния для ConversationHandler
QUESTION, MODERATION = range(2)

# Специальные отображения ID администраторов
ADMIN_USERNAME_MAP = {
    1292233190: "@x3klls",
    7805404869: "@hilliees",
    7691643567: "@anchous_faraon"
}

# Ссылка на чат для принятых заявок
CHAT_LINK = "https://t.me/+t4_PrY7o1NIwYzBi"

# Правила клана Minecraft dyO
CLAN_RULES = """
📜 ПРАВИЛА КЛАНА MINECRAFT dyO

⚠️ Вступив на сервер, автоматически соглашаетесь с правилами!

1.1 Публичное обсуждение состава сервера
🚫 Мут на всём сервере от 3 часов до 3 дней

1.2 Оскорбление участников сервера
🚫 Мут на всём сервере от 1 часа до 1 дня

1.3 Оскорбление и унижение родных участников сервера
🚫 Мут на всём сервере от 1 дня до 7 дней

1.4 Оскорбление и унижение состава сервера
🚫 Мут на всём сервере от 3 дней до 14 дней

1.5 Оскорбление и унижение родных состава сервера
🚫 Бан навсегда

1.6 Неконструктивная критика сервера или же его состава
🚫 Мут на всём сервере от 3 дней до 7 дней

1.7 Чрезмерное использование фото, видео, стикеров, эмодзи и т.п.
🚫 Мут на всём сервере от 30 минут до 3 часов

1.8 Капс(от 3 слов), спам, а также флуд сообщениями
🚫 Мут на всём сервере от 30 минут до 3 часов

1.9 Разжигание межнациональной, межрасовой, политической, религиозной розни
🚫 Мут на всём сервере от 1 дня до 7 дней

2.0 Использование команд сервера в обычном чате
🚫 Мут на всём сервере от 30 минут до 3 часов

2.1 Введение участников в заблуждение
🚫 Мут на всём сервере от 3 часов до 3 дней

2.2 Призыв не вступать в Discord Сервер
🚫 Мут на всём сервере от 1 дня до 3 дней

2.3 Чрезмерное упоминание состава сервера
🚫 Мут на всём сервере от 3 часов до 3 дней

2.4 Распространение личных данных игроков, угрозы
🚫 Бан навсегда

2.5 Выдача себя за состав сервера в корыстных целях
🚫 Бан от 7 дней до 30 дней

2.6 Использование нарушающих никнеймов
⚠️ Первое нарушение - предупреждение
🚫 Повторное - Бан от 7 дней до 14 дней

2.7 Обман администрации в корыстных целях
🚫 Бан от 3 до 10 дней

2.8 Введение администрации в заблуждение
🚫 Мут на всём сервере от 2 до 10 дней

🔧 МЕХАНИКА (Для модераторов и выше):

3.1 Некорректная выдача наказаний
⚠️ Предупреждение персоналу

3.2 Некорректное снятие наказаний
⚠️ 2 предупреждения персоналу

⚖️ ВАЖНОЕ:

• Незнание правил не освобождает от ответственности
• Администрация вправе выдавать наказания на своё усмотрение
• Администрация вправе изменять правила без оповещения
• Администрация вправе отказать в доступе без объяснения причин

🎯 При нарушении правил принимаются меры вплоть до ограничения доступа!
"""

class Database:
    def __init__(self, db_path="bot_database.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                application_text TEXT,
                status TEXT DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица вопросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question_text TEXT,
                status TEXT DEFAULT 'unanswered',
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица заблокированных пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS banned_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                reason TEXT,
                banned_by INTEGER,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")

    def execute_query(self, query, params=(), fetch=False):
        """Универсальный метод выполнения запросов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch:
            result = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            result = [dict(zip(columns, row)) for row in result]
        else:
            result = None
        
        conn.commit()
        conn.close()
        return result

    def add_user(self, user_id, username, first_name, last_name):
        """Добавление пользователя"""
        self.execute_query(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, last_name)
        )

    def add_application(self, user_id, application_text):
        """Добавление заявки"""
        self.execute_query(
            "INSERT INTO applications (user_id, application_text) VALUES (?, ?)",
            (user_id, application_text)
        )

    def add_question(self, user_id, question_text):
        """Добавление вопроса"""
        self.execute_query(
            "INSERT INTO questions (user_id, question_text) VALUES (?, ?)",
            (user_id, question_text)
        )

    def get_pending_applications(self):
        """Получение ожидающих заявок"""
        return self.execute_query(
            "SELECT a.*, u.username, u.first_name, u.last_name, "
            "ru.username as reviewer_username, ru.first_name as reviewer_first_name, ru.last_name as reviewer_last_name "
            "FROM applications a "
            "LEFT JOIN users u ON a.user_id = u.user_id "
            "LEFT JOIN users ru ON a.reviewed_by = ru.user_id "
            "WHERE a.status = 'pending' "
            "ORDER BY a.created_at",
            fetch=True
        )

    def get_unanswered_questions(self):
        """Получение неотвеченных вопросов"""
        return self.execute_query(
            "SELECT q.*, u.username, u.first_name, u.last_name, "
            "ru.username as reviewer_username, ru.first_name as reviewer_first_name, ru.last_name as reviewer_last_name "
            "FROM questions q "
            "LEFT JOIN users u ON q.user_id = u.user_id "
            "LEFT JOIN users ru ON q.reviewed_by = ru.user_id "
            "WHERE q.status = 'unanswered' "
            "ORDER BY q.created_at",
            fetch=True
        )

    def get_application(self, app_id):
        """Получение заявки по ID"""
        result = self.execute_query(
            "SELECT a.*, u.username FROM applications a "
            "LEFT JOIN users u ON a.user_id = u.user_id "
            "WHERE a.id = ?",
            (app_id,),
            fetch=True
        )
        return result[0] if result else None

    def get_question(self, question_id):
        """Получение вопроса по ID"""
        result = self.execute_query(
            "SELECT q.*, u.username FROM questions q "
            "LEFT JOIN users u ON q.user_id = u.user_id "
            "WHERE q.id = ?",
            (question_id,),
            fetch=True
        )
        return result[0] if result else None

    def get_admin_info(self, admin_id):
        """Получение информации об администраторе"""
        result = self.execute_query(
            "SELECT username, first_name, last_name FROM users WHERE user_id = ?",
            (admin_id,),
            fetch=True
        )
        return result[0] if result else None

    def update_application_status(self, app_id, status, reviewed_by=None):
        """Обновление статуса заявки"""
        if reviewed_by:
            self.execute_query(
                "UPDATE applications SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, reviewed_by, app_id)
            )
        else:
            self.execute_query(
                "UPDATE applications SET status = ? WHERE id = ?",
                (status, app_id)
            )

    def update_question_status(self, question_id, status, reviewed_by=None):
        """Обновление статуса вопроса"""
        if reviewed_by:
            self.execute_query(
                "UPDATE questions SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, reviewed_by, question_id)
            )
        else:
            self.execute_query(
                "UPDATE questions SET status = ? WHERE id = ?",
                (status, question_id)
            )

    def start_review_application(self, app_id, reviewer_id):
        """Начать рассмотрение заявки"""
        self.execute_query(
            "UPDATE applications SET reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (reviewer_id, app_id)
        )

    def start_review_question(self, question_id, reviewer_id):
        """Начать рассмотрение вопроса"""
        self.execute_query(
            "UPDATE questions SET reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (reviewer_id, question_id)
        )

    def get_all_users(self):
        """Получение всех пользователей"""
        return self.execute_query("SELECT user_id FROM users", fetch=True)

    def get_stats(self):
        """Получение статистики"""
        stats = {}
        
        result = self.execute_query("SELECT COUNT(*) as count FROM users", fetch=True)
        stats['total_users'] = result[0]['count'] if result else 0
        
        result = self.execute_query("SELECT COUNT(*) as count FROM applications", fetch=True)
        stats['total_applications'] = result[0]['count'] if result else 0
        
        result = self.execute_query("SELECT COUNT(*) as count FROM questions", fetch=True)
        stats['total_questions'] = result[0]['count'] if result else 0
        
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM applications WHERE status = 'pending'", 
            fetch=True
        )
        stats['pending_applications'] = result[0]['count'] if result else 0
        
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM questions WHERE status = 'unanswered'", 
            fetch=True
        )
        stats['unanswered_questions'] = result[0]['count'] if result else 0
        
        result = self.execute_query("SELECT COUNT(*) as count FROM banned_users", fetch=True)
        stats['banned_users'] = result[0]['count'] if result else 0
        
        return stats

    def ban_user(self, user_id, username, reason, banned_by):
        """Блокировка пользователя"""
        self.execute_query(
            "INSERT OR REPLACE INTO banned_users (user_id, username, reason, banned_by) VALUES (?, ?, ?, ?)",
            (user_id, username, reason, banned_by)
        )

    def unban_user(self, user_id):
        """Разблокировка пользователя"""
        self.execute_query(
            "DELETE FROM banned_users WHERE user_id = ?",
            (user_id,)
        )

    def is_user_banned(self, user_id):
        """Проверка заблокирован ли пользователь"""
        result = self.execute_query(
            "SELECT * FROM banned_users WHERE user_id = ?",
            (user_id,),
            fetch=True
        )
        return len(result) > 0

    def get_banned_users(self):
        """Получение списка заблокированных пользователей"""
        return self.execute_query(
            "SELECT bu.*, u.username as banned_by_username FROM banned_users bu "
            "LEFT JOIN users u ON bu.banned_by = u.user_id "
            "ORDER BY bu.banned_at DESC",
            fetch=True
        )

    def get_user_by_username(self, username):
        """Получение пользователя по username"""
        result = self.execute_query(
            "SELECT * FROM users WHERE username = ?",
            (username.lstrip('@'),),
            fetch=True
        )
        return result[0] if result else None

# Инициализация базы данных
db = Database()

class MinecraftBot:
    def __init__(self):
        self.application = None

    def setup_handlers(self):
        """Настройка обработчиков"""
        conv_handler = ConversationHandler(
            entry_points=[
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            ],
            states={
                QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_question)],
                MODERATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_moderation)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("admin", self.admin_panel))
        self.application.add_handler(CommandHandler("stats", self.stats))
        self.application.add_handler(CommandHandler("addadmin", self.add_admin))
        self.application.add_handler(CommandHandler("rules", self.show_rules))
        self.application.add_handler(CommandHandler("ban", self.ban_user_command))
        self.application.add_handler(CommandHandler("unban", self.unban_user_command))
        self.application.add_handler(CommandHandler("banned", self.show_banned_users))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        self.application.add_handler(conv_handler)

    def main_keyboard(self, user_id):
        """Основная клавиатура с учетом прав администратора"""
        if user_id in ADMIN_IDS:
            # Клавиатура для администраторов
            keyboard = [
                [KeyboardButton("❓ Вопрос"), KeyboardButton("📝 Набор в модерацию")],
                [KeyboardButton("📜 Правила клана"), KeyboardButton("👑 Панель администратора")]
            ]
        else:
            # Клавиатура для обычных пользователей
            keyboard = [
                [KeyboardButton("❓ Вопрос"), KeyboardButton("📝 Набор в модерацию")],
                [KeyboardButton("📜 Правила клана")]
            ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def admin_keyboard(self):
        """Клавиатура админ-панели"""
        keyboard = [
            [InlineKeyboardButton("📋 Заявки", callback_data="admin_applications")],
            [InlineKeyboardButton("❓ Вопросы", callback_data="admin_questions")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🚫 Заблокированные", callback_data="admin_banned")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def cancel_keyboard(self):
        """Клавиатура для отмены действия"""
        keyboard = [[KeyboardButton("❌ Отменить")]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def format_admin_name(self, admin_id, admin_info=None):
        """Форматирование имени администратора с учетом специальных ID"""
        # Проверяем специальные ID
        if admin_id in ADMIN_USERNAME_MAP:
            return ADMIN_USERNAME_MAP[admin_id]
        
        # Если нет специального отображения, используем информацию из базы
        if not admin_info:
            admin_info = db.get_admin_info(admin_id)
        
        if not admin_info:
            return f"Администратор (ID: {admin_id})"
        
        username = admin_info.get('username')
        first_name = admin_info.get('first_name')
        last_name = admin_info.get('last_name')
        
        if username:
            return f"@{username}"
        elif first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        else:
            return f"Администратор (ID: {admin_id})"

    async def notify_admins_about_review(self, reviewer_id, item_type, item_id, item_info):
        """Уведомление администраторов о начале рассмотрения заявки/вопроса"""
        reviewer_name = self.format_admin_name(reviewer_id)
        
        if item_type == "application":
            message = (
                f"🔍 Администратор {reviewer_name} начал рассмотрение заявки #{item_id}\n"
                f"👤 Кандидат: @{item_info['username']} (ID: {item_info['user_id']})\n"
                f"📅 Время создания: {item_info['created_at']}"
            )
        elif item_type == "question":
            message = (
                f"🔍 Администратор {reviewer_name} начал рассмотрение вопроса #{item_id}\n"
                f"👤 Автор: @{item_info['username']} (ID: {item_info['user_id']})\n"
                f"📅 Время создания: {item_info['created_at']}"
            )
        else:
            return
        
        # Уведомляем всех админов кроме того, кто начал рассмотрение
        for admin_id in ADMIN_IDS:
            if admin_id != reviewer_id:
                try:
                    await self.application.bot.send_message(admin_id, message)
                except Exception as e:
                    logger.error(f"Ошибка уведомления админа {admin_id}: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user
        
        # Проверяем заблокирован ли пользователь
        if db.is_user_banned(user.id):
            await update.message.reply_text("❌ Вы заблокированы и не можете использовать этого бота.")
            return
        
        db.add_user(user.id, user.username, user.first_name, user.last_name)
        
        welcome_text = "Привет! Это бот клана Minecraft dyO.\nВыберите опцию:"
        
        if user.id in ADMIN_IDS:
            welcome_text += "\n\n👑 У вас есть права администратора!"
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=self.main_keyboard(user.id)
        )

    async def show_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать правила клана"""
        user_id = update.message.from_user.id
        
        # Проверяем заблокирован ли пользователь
        if db.is_user_banned(user_id):
            await update.message.reply_text("❌ Вы заблокированы и не можете использовать этого бота.")
            return
        
        # Разбиваем правила на части, если они слишком длинные для одного сообщения
        if len(CLAN_RULES) > 4000:
            rules_parts = [CLAN_RULES[i:i+4000] for i in range(0, len(CLAN_RULES), 4000)]
            for i, part in enumerate(rules_parts):
                if i == 0:
                    await update.message.reply_text(part)
                else:
                    await update.message.reply_text(part)
        else:
            await update.message.reply_text(CLAN_RULES)
        
        await update.message.reply_text(
            "Выберите дальнейшее действие:",
            reply_markup=self.main_keyboard(user_id)
        )

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return

        await update.message.reply_text(
            "👑 Панель администратора:",
            reply_markup=self.admin_keyboard()
        )

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return

        stats = db.get_stats()
        await update.message.reply_text(
            f"📊 Статистика бота:\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"📝 Заявок: {stats['total_applications']}\n"
            f"❓ Вопросов: {stats['total_questions']}\n"
            f"⏳ Новых заявок: {stats['pending_applications']}\n"
            f"⏳ Новых вопросов: {stats['unanswered_questions']}\n"
            f"🚫 Заблокированных: {stats['banned_users']}"
        )

    async def add_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для добавления администратора"""
        user_id = update.message.from_user.id
        
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ У вас нет прав для этой команды.")
            return
        
        if not context.args:
            await update.message.reply_text("Использование: /addadmin <user_id>")
            return
        
        try:
            new_admin_id = int(context.args[0])
            if new_admin_id not in ADMIN_IDS:
                ADMIN_IDS.append(new_admin_id)
                await update.message.reply_text(f"✅ Пользователь {new_admin_id} добавлен в администраторы.")
            else:
                await update.message.reply_text("❌ Этот пользователь уже администратор.")
        except ValueError:
            await update.message.reply_text("❌ Неверный ID пользователя.")

    async def ban_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для блокировки пользователя"""
        user_id = update.message.from_user.id
        
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ У вас нет прав для этой команды.")
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("Использование: /ban @username причина_блокировки")
            return
        
        username = context.args[0]
        reason = ' '.join(context.args[1:])
        
        # Получаем информацию о пользователе
        user_info = db.get_user_by_username(username)
        if not user_info:
            await update.message.reply_text("❌ Пользователь с таким username не найден.")
            return
        
        # Блокируем пользователя
        db.ban_user(user_info['user_id'], user_info['username'], reason, user_id)
        
        admin_name = self.format_admin_name(user_id)
        await update.message.reply_text(
            f"✅ Пользователь @{user_info['username']} (ID: {user_info['user_id']}) заблокирован.\n"
            f"👮‍♂️ Заблокировал: {admin_name}\n"
            f"📝 Причина: {reason}"
        )
        
        # Уведомляем всех админов
        for admin_id in ADMIN_IDS:
            if admin_id != user_id:
                try:
                    await self.application.bot.send_message(
                        admin_id,
                        f"🚫 Пользователь @{user_info['username']} заблокирован администратором {admin_name}\n"
                        f"📝 Причина: {reason}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка уведомления админа {admin_id}: {e}")

    async def unban_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для разблокировки пользователя"""
        user_id = update.message.from_user.id
        
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ У вас нет прав для этой команды.")
            return
        
        if not context.args:
            await update.message.reply_text("Использование: /unban @username")
            return
        
        username = context.args[0]
        
        # Получаем информацию о пользователе
        user_info = db.get_user_by_username(username)
        if not user_info:
            await update.message.reply_text("❌ Пользователь с таким username не найден.")
            return
        
        # Проверяем заблокирован ли пользователь
        if not db.is_user_banned(user_info['user_id']):
            await update.message.reply_text("❌ Этот пользователь не заблокирован.")
            return
        
        # Разблокируем пользователя
        db.unban_user(user_info['user_id'])
        
        admin_name = self.format_admin_name(user_id)
        await update.message.reply_text(
            f"✅ Пользователь @{user_info['username']} (ID: {user_info['user_id']}) разблокирован.\n"
            f"👮‍♂️ Разблокировал: {admin_name}"
        )

    async def show_banned_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список заблокированных пользователей"""
        user_id = update.message.from_user.id
        
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return

        banned_users = db.get_banned_users()
        if not banned_users:
            await update.message.reply_text("✅ Нет заблокированных пользователей.")
            return

        banned_list = "🚫 ЗАБЛОКИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ:\n\n"
        for banned in banned_users:
            banned_by = f"@{banned['banned_by_username']}" if banned['banned_by_username'] else f"ID: {banned['banned_by']}"
            banned_list += (
                f"👤 Пользователь: @{banned['username']} (ID: {banned['user_id']})\n"
                f"📝 Причина: {banned['reason']}\n"
                f"👮‍♂️ Заблокировал: {banned_by}\n"
                f"📅 Дата: {banned['banned_at']}\n"
                f"────────────────────\n"
            )

        await update.message.reply_text(banned_list)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        
        if query.data == "admin_back":
            await query.edit_message_text(
                "Возврат в главное меню:",
                reply_markup=None
            )
            await query.message.reply_text(
                "👑 Панель администратора закрыта.",
                reply_markup=self.main_keyboard(user_id)
            )
            return

        if user_id not in ADMIN_IDS:
            await query.edit_message_text("❌ У вас нет прав администратора.")
            return

        data = query.data

        if data == "admin_applications":
            await self.show_applications(query, context)
        elif data == "admin_questions":
            await self.show_questions(query, context)
        elif data == "admin_stats":
            await self.show_stats(query, context)
        elif data == "admin_banned":
            await self.show_banned_users_callback(query, context)
        elif data.startswith("app_"):
            await self.handle_application_action(query, data, context)
        elif data.startswith("question_"):
            await self.handle_question_action(query, data, context)
        else:
            # Если callback_data не распознан
            await query.edit_message_text(
                "❌ Неизвестная команда. Попробуйте снова.",
                reply_markup=self.admin_keyboard()
            )

    async def show_banned_users_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показать список заблокированных пользователей через callback"""
        banned_users = db.get_banned_users()
        if not banned_users:
            await query.edit_message_text("✅ Нет заблокированных пользователей.", reply_markup=self.admin_keyboard())
            return

        banned_list = "🚫 ЗАБЛОКИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ:\n\n"
        for banned in banned_users:
            banned_by = f"@{banned['banned_by_username']}" if banned['banned_by_username'] else f"ID: {banned['banned_by']}"
            banned_list += (
                f"👤 Пользователь: @{banned['username']} (ID: {banned['user_id']})\n"
                f"📝 Причина: {banned['reason']}\n"
                f"👮‍♂️ Заблокировал: {banned_by}\n"
                f"📅 Дата: {banned['banned_at']}\n"
                f"────────────────────\n"
            )

        await query.edit_message_text(banned_list, reply_markup=self.admin_keyboard())

    async def show_applications(self, query, context: ContextTypes.DEFAULT_TYPE):
        try:
            applications = db.get_pending_applications()
            if not applications:
                await query.edit_message_text("✅ Нет новых заявок.", reply_markup=self.admin_keyboard())
                return

            app = applications[0]
            
            # Получаем информацию о рассматривающем администраторе
            reviewer_info = ""
            if app['reviewed_by']:
                reviewer_name = self.format_admin_name(app['reviewed_by'])
                reviewer_info = f"\n👤 Рассматривает: {reviewer_name}"
            
            keyboard = [
                [
                    InlineKeyboardButton("👀 Рассмотреть", callback_data=f"app_review_{app['id']}"),
                ],
                [
                    InlineKeyboardButton("✅ Принять", callback_data=f"app_approve_{app['id']}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"app_reject_{app['id']}")
                ],
                [InlineKeyboardButton("⏭️ Следующая", callback_data="admin_applications")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            full_name = f"{app['first_name'] or ''} {app['last_name'] or ''}".strip()
            username = f"@{app['username']}" if app['username'] else "без username"
            text = (f"📝 Заявка #{app['id']}\n"
                    f"👤: {full_name} ({username})\n"
                    f"🆔: {app['user_id']}\n"
                    f"📅: {app['created_at']}"
                    f"{reviewer_info}\n\n"
                    f"📄 Анкета:\n{app['application_text']}")

            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка при показе заявок: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при загрузке заявок.",
                reply_markup=self.admin_keyboard()
            )

    async def show_questions(self, query, context: ContextTypes.DEFAULT_TYPE):
        try:
            questions = db.get_unanswered_questions()
            if not questions:
                await query.edit_message_text("✅ Нет новых вопросов.", reply_markup=self.admin_keyboard())
                return

            question = questions[0]
            
            # Получаем информацию о рассматривающем администраторе
            reviewer_info = ""
            if question['reviewed_by']:
                reviewer_name = self.format_admin_name(question['reviewed_by'])
                reviewer_info = f"\n👤 Рассматривает: {reviewer_name}"
            
            keyboard = [
                [
                    InlineKeyboardButton("👀 Рассмотреть", callback_data=f"question_review_{question['id']}"),
                ],
                [
                    InlineKeyboardButton("✅ Ответить", callback_data=f"question_answer_{question['id']}"),
                    InlineKeyboardButton("❌ Удалить", callback_data=f"question_delete_{question['id']}")
                ],
                [InlineKeyboardButton("⏭️ Следующий", callback_data="admin_questions")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            full_name = f"{question['first_name'] or ''} {question['last_name'] or ''}".strip()
            username = f"@{question['username']}" if question['username'] else "без username"
            text = (f"❓ Вопрос #{question['id']}\n"
                    f"👤: {full_name} ({username})\n"
                    f"🆔: {question['user_id']}\n"
                    f"📅: {question['created_at']}"
                    f"{reviewer_info}\n\n"
                    f"📄 Вопрос:\n{question['question_text']}")

            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Ошибка при показе вопросов: {e}")
            await query.edit_message_text(
                "❌ Произошла ошибка при загрузке вопросов.",
                reply_markup=self.admin_keyboard()
            )

    async def show_stats(self, query, context: ContextTypes.DEFAULT_TYPE):
        stats = db.get_stats()
        text = (f"📊 Статистика бота:\n"
                f"👥 Пользователей: {stats['total_users']}\n"
                f"📝 Заявок: {stats['total_applications']}\n"
                f"❓ Вопросов: {stats['total_questions']}\n"
                f"⏳ Новых заявок: {stats['pending_applications']}\n"
                f"⏳ Новых вопросов: {stats['unanswered_questions']}\n"
                f"🚫 Заблокированных: {stats['banned_users']}")
        
        await query.edit_message_text(text, reply_markup=self.admin_keyboard())

    async def handle_application_action(self, query, data, context: ContextTypes.DEFAULT_TYPE):
        user_id = query.from_user.id
        action, app_id = data.split("_")[1], int(data.split("_")[2])
        application = db.get_application(app_id)
        
        if action == "review":
            # Начать рассмотрение заявки
            db.start_review_application(app_id, user_id)
            
            # Получаем информацию об администраторе для уведомления
            admin_name = self.format_admin_name(user_id)
            
            # Уведомляем пользователя
            try:
                await self.application.bot.send_message(
                    application['user_id'],
                    f"🔍 Ваша заявка на модерацию взята в рассмотрение администратором {admin_name}. Ожидайте решения!"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю: {e}")
            
            # УВЕДОМЛЯЕМ ДРУГИХ АДМИНИСТРАТОРОВ О НАЧАЛЕ РАССМОТРЕНИЯ
            await self.notify_admins_about_review(user_id, "application", app_id, application)
            
            await query.edit_message_text(
                f"👀 Вы начали рассмотрение заявки #{app_id}",
                reply_markup=self.admin_keyboard()
            )
            
        elif action == "approve":
            db.update_application_status(app_id, "approved", user_id)
            
            # Получаем информацию об администраторе для уведомления
            admin_name = self.format_admin_name(user_id)
            
            try:
                await self.application.bot.send_message(
                    application['user_id'],
                    f"🎉 Ваша заявка на модерацию одобрена администратором {admin_name}!\n\n"
                    f"📝 Ссылка на чат: {CHAT_LINK}\n\n"
                    f"Присоединяйтесь к нашему чату для дальнейших инструкций!"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю: {e}")
            
            # Уведомляем всех админов о принятии заявки
            applicant_info = db.get_admin_info(application['user_id'])
            applicant_name = f"@{applicant_info['username']}" if applicant_info and applicant_info.get('username') else f"ID: {application['user_id']}"
            
            for admin_id in ADMIN_IDS:
                if admin_id != user_id:
                    try:
                        await self.application.bot.send_message(
                            admin_id,
                            f"✅ Заявка на модерацию одобрена!\n"
                            f"👤 Кандидат: {applicant_name}\n"
                            f"👮‍♂️ Одобрил: {admin_name}\n"
                            f"📅 Время: {application['created_at']}"
                        )
                    except Exception as e:
                        logger.error(f"Ошибка уведомления админа {admin_id}: {e}")
            
            await query.edit_message_text(f"✅ Заявка #{app_id} одобрена.", reply_markup=self.admin_keyboard())
            
        elif action == "reject":
            db.update_application_status(app_id, "rejected", user_id)
            
            # Получаем информацию об администраторе для уведомления
            admin_name = self.format_admin_name(user_id)
            
            try:
                await self.application.bot.send_message(
                    application['user_id'],
                    f"❌ К сожалению, ваша заявка на модерацию отклонена администратором {admin_name}."
                )
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю: {e}")
            
            # Уведомляем всех админов об отклонении заявки
            applicant_info = db.get_admin_info(application['user_id'])
            applicant_name = f"@{applicant_info['username']}" if applicant_info and applicant_info.get('username') else f"ID: {application['user_id']}"
            
            for admin_id in ADMIN_IDS:
                if admin_id != user_id:
                    try:
                        await self.application.bot.send_message(
                            admin_id,
                            f"❌ Заявка на модерацию отклонена!\n"
                            f"👤 Кандидат: {applicant_name}\n"
                            f"👮‍♂️ Отклонил: {admin_name}\n"
                            f"📅 Время: {application['created_at']}"
                        )
                    except Exception as e:
                        logger.error(f"Ошибка уведомления админа {admin_id}: {e}")
            
            await query.edit_message_text(f"❌ Заявка #{app_id} отклонена.", reply_markup=self.admin_keyboard())

    async def handle_question_action(self, query, data, context: ContextTypes.DEFAULT_TYPE):
        user_id = query.from_user.id
        action, question_id = data.split("_")[1], int(data.split("_")[2])
        question = db.get_question(question_id)
        
        if action == "review":
            # Начать рассмотрение вопроса
            db.start_review_question(question_id, user_id)
            
            # Получаем информацию об администраторе для уведомления
            admin_name = self.format_admin_name(user_id)
            
            # Уведомляем пользователя
            try:
                await self.application.bot.send_message(
                    question['user_id'],
                    f"🔍 Ваш вопрос взят в рассмотрение администратором {admin_name}. Скоро вы получите ответ!"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю: {e}")
            
            # УВЕДОМЛЯЕМ ДРУГИХ АДМИНИСТРАТОРОВ О НАЧАЛЕ РАССМОТРЕНИЯ
            await self.notify_admins_about_review(user_id, "question", question_id, question)
            
            await query.edit_message_text(
                f"👀 Вы начали рассмотрение вопроса #{question_id}",
                reply_markup=self.admin_keyboard()
            )
            
        elif action == "answer":
            context.user_data['answering_question'] = question_id
            await query.edit_message_text(
                f"💬 Введите ответ на вопрос от @{question['username']}:"
            )
        elif action == "delete":
            db.update_question_status(question_id, "deleted", user_id)
            
            # Получаем информацию об администраторе для уведомления
            admin_name = self.format_admin_name(user_id)
            
            await query.edit_message_text(f"✅ Вопрос #{question_id} удален администратором {admin_name}.", reply_markup=self.admin_keyboard())

    async def question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user
        
        # Проверяем заблокирован ли пользователь
        if db.is_user_banned(user.id):
            await update.message.reply_text("❌ Вы заблокированы и не можете использовать этого бота.")
            return ConversationHandler.END
        
        await update.message.reply_text(
            "Задайте ваш вопрос и администрация клана ответит вам в ближайшее время:\n\n"
            "Или нажмите '❌ Отменить' для возврата в главное меню.",
            reply_markup=self.cancel_keyboard()
        )
        return QUESTION

    async def receive_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user
        text = update.message.text
        
        # Проверяем заблокирован ли пользователь
        if db.is_user_banned(user.id):
            await update.message.reply_text("❌ Вы заблокированы и не можете использовать этого бота.")
            return ConversationHandler.END
        
        # Проверяем отмену
        if text == "❌ Отменить":
            await update.message.reply_text(
                "❌ Создание вопроса отменено.",
                reply_markup=self.main_keyboard(user.id)
            )
            return ConversationHandler.END
        
        db.add_question(user.id, text)
        
        # Уведомляем пользователя
        await update.message.reply_text(
            "✅ Ваш вопрос отправлен администрации и находится на рассмотрении. Ожидайте ответа!",
            reply_markup=self.main_keyboard(user.id)
        )
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            try:
                await self.application.bot.send_message(
                    admin_id,
                    f"❓ Новый вопрос от @{user.username}:\n\n{text}"
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления админа {admin_id}: {e}")
        
        return ConversationHandler.END

    async def moderation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user
        
        # Проверяем заблокирован ли пользователь
        if db.is_user_banned(user.id):
            await update.message.reply_text("❌ Вы заблокированы и не можете использовать этого бота.")
            return ConversationHandler.END
        
        await update.message.reply_text(
            "📝 Заполните анкету для подачи заявки в модераторы:\n\n"
            "При написании заявки необходимо соблюдать все правила русского языка.\n"
            "1. Ваш ник: \n"
            "2. Ваш возраст:\n"
            "3. Почему Вы хотите стать модератором?:\n"
            "4. Дайте определение словам Бан/Мут/Варн:\n"
            "5. Есть опыт модерирования?:\n"
            "6. Напишите небольшой рассказ о себе(не менее двадцати слов)\n"
            "7. Сколько времени Вы, готовы уделять набору в клан?\n"
            "8. Почему именно наш клан?\n\n"
            "!ВАЖНО!\n"
            "Если вашу заявку одобряют, то вы становитесь на пост стажёра клана.\n"
            "На стажёрке нельзя брать отгулы.\n"
            "Максимальное время на стажировке - 1 неделя\n"
            "Получение 1 выговора на стажёре - снятие\n\n"
            "Отправьте всю информацию одним сообщением."
            "Или нажмите '❌ Отменить' для возврата в главное меню.",
            reply_markup=self.cancel_keyboard()
        )
        return MODERATION

    async def receive_moderation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user
        text = update.message.text
        
        # Проверяем заблокирован ли пользователь
        if db.is_user_banned(user.id):
            await update.message.reply_text("❌ Вы заблокированы и не можете использовать этого бота.")
            return ConversationHandler.END
        
        # Проверяем отмену
        if text == "❌ Отменить":
            await update.message.reply_text(
                "❌ Подача заявки отменена.",
                reply_markup=self.main_keyboard(user.id)
            )
            return ConversationHandler.END
        
        db.add_application(user.id, text)
        
        # Уведомляем пользователя
        await update.message.reply_text(
            "✅ Ваша заявка отправлена на рассмотрение! "
            "Администрация свяжется с вами в ближайшее время.",
            reply_markup=self.main_keyboard(user.id)
        )
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            try:
                await self.application.bot.send_message(
                    admin_id,
                    f"📝 Новая заявка в модерацию от @{user.username}:\n\n{text}"
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления админа {admin_id}: {e}")
        
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        await update.message.reply_text(
            "Диалог отменен.",
            reply_markup=self.main_keyboard(user_id)
        )
        return ConversationHandler.END

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        text = update.message.text
        
        # Проверяем заблокирован ли пользователь
        if db.is_user_banned(user_id):
            await update.message.reply_text("❌ Вы заблокированы и не можете использовать этого бота.")
            return
        
        # Обработка ответа на вопрос
        if 'answering_question' in context.user_data:
            question_id = context.user_data.pop('answering_question')
            question = db.get_question(question_id)
            
            try:
                await self.application.bot.send_message(
                    question['user_id'],
                    f"💬 Ответ от администрации на ваш вопрос:\n\n{text}"
                )
                db.update_question_status(question_id, "answered", user_id)
                await update.message.reply_text("✅ Ответ отправлен пользователю.", reply_markup=self.main_keyboard(user_id))
            except Exception as e:
                await update.message.reply_text("❌ Ошибка отправки ответа.", reply_markup=self.main_keyboard(user_id))
            return
        
        # Основные кнопки
        if text == "❓ Вопрос":
            return await self.question(update, context)
        elif text == "📝 Набор в модерацию":
            return await self.moderation(update, context)
        elif text == "📜 Правила клана":
            await self.show_rules(update, context)
        elif text == "👑 Панель администратора" and user_id in ADMIN_IDS:
            await self.admin_panel(update, context)
        else:
            await update.message.reply_text(
                "Используйте кнопки для навигации:",
                reply_markup=self.main_keyboard(user_id)
            )

    def run(self):
        """Запуск бота"""
        if BOT_TOKEN == "ВАШ_ТОКЕН_БОТА_ЗДЕСЬ":
            print("❌ ОШИБКА: Замените BOT_TOKEN на реальный токен вашего бота!")
            print("1. Создайте бота через @BotFather в Telegram")
            print("2. Получите токен")
            print("3. Замените строку BOT_TOKEN в коде на ваш токен")
            return
        
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        
        print("✅ Бот запущен...")
        print("🤖 Бот готов к работе!")
        print("👑 Администраторы:", ADMIN_IDS)
        print("🔧 Специальные отображения:", ADMIN_USERNAME_MAP)
        print("💬 Ссылка на чат:", CHAT_LINK)
        
        self.application.run_polling()

if __name__ == '__main__':
    bot = MinecraftBot()
    bot.run()
