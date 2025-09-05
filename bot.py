import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import re

# Bot settings
BOT_TOKEN = "8069419306:AAFbTMN4BbQ2zIInV_ddJ_WO8jESmaDAsIA"  # ضع التوكن هنا مباشرة
SECRET_KEY = "your_super_secret_key_here"  # وضع المفتاح السري هنا

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask application setup for webhook
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

# --- In-memory storage (no database) ---
# Define roles and permissions
ROLES = {
    "User": {"level": 1},
    "Special": {"level": 2},
    "Admin": {"level": 3},
    "Manager": {"level": 4},
    "Creator": {"level": 5},
    "Supervisor": {"level": 6},
    "Owner": {"level": 7},
    "Dev": {"level": 8}
}

PERMISSIONS = {
    "use_bot": {"roles": ["User", "Special", "Admin", "Manager", "Creator", "Supervisor", "Owner", "Dev"]},
    "entertainment_commands": {"roles": ["Special", "Admin", "Manager", "Creator", "Supervisor", "Owner", "Dev"]},
    "settings_commands": {"roles": ["Admin", "Manager", "Creator", "Supervisor", "Owner", "Dev"]},
    "lock_unlock_commands": {"roles": ["Admin", "Manager", "Creator", "Supervisor", "Owner", "Dev"]},
    "admin_commands": {"roles": ["Admin", "Manager", "Creator", "Supervisor", "Owner", "Dev"]},
    "dev_commands": {"roles": ["Dev"]},
    "manage_ranks": {"roles": ["Dev"]}
}

USERS_DATA = {
    5032833915: {"role": "Dev", "first_name": "Owner", "last_name": None, "username": None}  # معرف المالك
}

COMMANDS_CONTENT = {
    "admin": """
    • مرحبًا بك، قائمة أوامر الإدارة:
    ... (بقية المحتوى) ...
    """,
    "settings": """
    مرحبًا بك في قائمة أوامر الإعدادات:
    ... (بقية المحتوى) ...
    """,
    "lock_unlock": """
    مرحبًا بك في قائمة القفل/الفتح:
    ... (بقية المحتوى) ...
    """,
    "entertainment": """
    • مرحبًا أيها المستخدم العزيز!
    - أوامر التسلية:
    ... (بقية المحتوى) ...
    """,
    "dev": """
    مرحباً أيها المطور العزيز!
    ... (بقية المحتوى) ...
    """
}

# --- Helper functions for permissions ---
def get_user_role_name(user_id):
    return USERS_DATA.get(user_id, {}).get("role", "User")

def has_permission(user_id, permission_name):
    role_name = get_user_role_name(user_id)
    if role_name in ["Dev", "Owner"]:
        return True
    return role_name in PERMISSIONS.get(permission_name, {}).get("roles", [])

def get_user_level(user_id):
    role_name = get_user_role_name(user_id)
    return ROLES.get(role_name, {}).get("level", 1)

def get_role_by_level(level):
    for role, data in ROLES.items():
        if data["level"] == level:
            return role
    return "User"

def get_role_by_name(name):
    return ROLES.get(name, {}).get("level")

# --- Bot functions (Telegram Handlers) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    if user_id not in USERS_DATA:
        USERS_DATA[user_id] = {
            "role": "User",
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username
        }
        logger.info(f"New user added: {user_id}")
    else:
        USERS_DATA[user_id]["first_name"] = user.first_name
        USERS_DATA[user_id]["last_name"] = user.last_name
        USERS_DATA[user_id]["username"] = user.username

    await update.message.reply_text(f"مرحباً بك {user.first_name} في بوت الأوامر.")

async def show_main_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not has_permission(user_id, "use_bot"):
        await update.message.reply_text("عذراً، لا تمتلك صلاحية استخدام هذا الأمر.")
        return

    keyboard = [
        [InlineKeyboardButton("أوامر الإدارة", callback_data="cmd_admin")],
        [InlineKeyboardButton("أوامر الإعدادات", callback_data="cmd_settings")],
        [InlineKeyboardButton("أوامر القفل/الفتح", callback_data="cmd_lock_unlock")],
        [InlineKeyboardButton("أوامر التسلية", callback_data="cmd_entertainment")],
        [InlineKeyboardButton("أوامر المطورين", callback_data="cmd_dev")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("هنا قوائم الأوامر:", reply_markup=reply_markup)

async def handle_command_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    command_name = query.data.replace("cmd_", "")
    command_content = COMMANDS_CONTENT.get(command_name)

    if not command_content:
        await query.edit_message_text("عذراً، هذا الأمر غير موجود.")
        return

    permission_map = {
        "admin": "admin_commands", "settings": "settings_commands", "lock_unlock": "lock_unlock_commands",
        "entertainment": "entertainment_commands", "dev": "dev_commands",
    }
    required_permission = permission_map.get(command_name)
    if required_permission and not has_permission(user_id, required_permission):
        await query.edit_message_text("عذراً، لا تمتلك صلاحية عرض هذه الأوامر.")
        return

    keyboard = [[InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(command_content, reply_markup=reply_markup)

async def handle_text_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if text.lower() == "اوامر":
        await show_main_commands(update, context)
    elif text.lower() == "رتبتي":
        await get_my_rank(update, context)
    elif text.lower() == "رتبته":
        await get_other_rank(update, context)
    elif text.lower().startswith("رفع"):
        context.args = text.split()[1:]
        await promote_user(update, context)
    elif text.lower().startswith("تنزيل"):
        context.args = text.split()[1:]
        await demote_user(update, context)
    else:
        pass

async def get_my_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    role_name = get_user_role_name(user_id)
    await update.message.reply_text(f"رتبتك هي: {role_name}")

async def get_other_rank(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not update.message.reply_to_message:
        await update.message.reply_text("الرجاء الرد على المستخدم الذي تريد معرفة رتبته.")
        return

    target_user_id = update.message.reply_to_message.from_user.id
    target_user_role = get_user_role_name(target_user_id)

    target_user_name = update.message.reply_to_message.from_user.first_name
    await update.message.reply_text(f"رتبة {target_user_name} هي: {target_user_role}")

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not has_permission(user_id, "manage_ranks"):
        await update.message.reply_text("عذراً، لا تمتلك صلاحية إدارة الرتب.")
        return

    if not context.args:
        await update.message.reply_text("الرجاء تحديد رتبة. مثال: رفع ديف")
        return

    target_role_name = context.args[0].capitalize()

    if not update.message.reply_to_message:
        await update.message.reply_text("الرجاء الرد على المستخدم الذي تريد ترقيته.")
        return

    target_user_id = update.message.reply_to_message.from_user.id
    target_user_name = update.message.reply_to_message.from_user.first_name

    current_role_level = get_user_level(user_id)
    target_role_level = get_role_by_name(target_role_name)

    if not target_role_level:
        await update.message.reply_text("الرتبة غير موجودة. الرجاء التحقق من الرتب المتاحة.")
        return

    if target_role_level >= current_role_level:
        await update.message.reply_text("لا يمكنك ترقية مستخدم إلى رتبة تساوي أو أعلى من رتبتك.")
        return

    USERS_DATA[target_user_id] = {"role": target_role_name}
    await update.message.reply_text(f"تمت ترقية {target_user_name} بنجاح إلى: {target_role_name}")

async def demote_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not has_permission(user_id, "manage_ranks"):
        await update.message.reply_text("عذراً، لا تمتلك صلاحية إدارة الرتب.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("الرجاء الرد على المستخدم الذي تريد تخفيض رتبته.")
        return

    target_user_id = update.message.reply_to_message.from_user.id
    target_user_name = update.message.reply_to_message.from_user.first_name

    target_user_role = get_user_role_name(target_user_id)
    target_role_level = get_user_level(target_user_id)
    current_role_level = get_user_level(user_id)

    if target_role_level >= current_role_level:
        await update.message.reply_text("لا يمكنك تخفيض رتبة مستخدم إذا كانت رتبته تساوي أو أعلى من رتبتك.")
        return

    USERS_DATA[target_user_id] = {"role": "User"}
    await update.message.reply_text(f"تم تخفيض رتبة {target_user_name} بنجاح إلى: User")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"An error occurred: {context.error}", exc_info=context.error)

# --- Webhook setup and startup ---
application = Application.builder().token(BOT_TOKEN).build()

# Standard English commands
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("commands", show_main_commands))

# Callback queries for inline keyboard
application.add_handler(CallbackQueryHandler(handle_command_query, pattern="^cmd_"))
application.add_handler(CallbackQueryHandler(show_main_commands, pattern="^main_menu$"))

# Arabic commands using Regex
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^(اوامر|رتبتي|رتبته|رفع|تنزيل)', flags=re.IGNORECASE), handle_text_commands))
application.add_error_handler(error_handler)
@app.route(f"/{SECRET_KEY}", methods=["POST"])
def webhook_handler():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.process_update(update)
    return "ok"

if __name__ == '__main__':
    port = os.getenv("PORT", 5000)
    app.run(host='0.0.0.0', port=port)
