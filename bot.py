import os
import logging
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime, timedelta

# إعدادات البوت (تم تضمينها مباشرة بناءً على طلبك)
BOT_TOKEN = "8069419306:AAFbTMN4BbQ2zIInV_ddJ_WO8jESmaDAsIA"
OWNER_USER_ID = 5032833915
SECRET_KEY = "your_super_secret_key_here" # يمكنك تغيير هذا المفتاح السري

# إعداد التسجيل (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# إعداد تطبيق Flask وقاعدة البيانات
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database/app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = SECRET_KEY
db = SQLAlchemy(app)

# --- نماذج قاعدة البيانات ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), default=1) # Default to User role
    role = db.relationship("Role", backref="users")

    def __repr__(self):
        return f"<User {self.telegram_id} ({self.username or self.first_name})>"

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    level = db.Column(db.Integer, unique=True, nullable=False)

    def __repr__(self):
        return f"<Role {self.name} (Level {self.level})>"

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Permission {self.name}>"

class RolePermission(db.Model):
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey("permission.id"), primary_key=True)

    role = db.relationship("Role", backref=db.backref("role_permissions", lazy=True))
    permission = db.relationship("Permission", backref=db.backref("permission_roles", lazy=True))

    def __repr__(self):
        return f"<Role {self.role_id} - Permission {self.permission_id}>"

class Command(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Command {self.name}>"

# --- وظائف مساعدة للصلاحيات ---

def get_user_role(telegram_id):
    with app.app_context():
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if user and user.role:
            return user.role
        return Role.query.filter_by(name="User").first() # Default to User role if not found

def has_permission(telegram_id, permission_name):
    with app.app_context():
        role = get_user_role(telegram_id)
        if not role:
            return False
        
        # Owner and Dev roles have all permissions
        if role.name in ["Owner", "Dev"]:
            return True

        permission = Permission.query.filter_by(name=permission_name).first()
        if not permission:
            return False
        
        return RolePermission.query.filter_by(role_id=role.id, permission_id=permission.id).first() is not None

def get_role_by_level(level):
    return Role.query.filter_by(level=level).first()

def get_role_by_name(name):
    return Role.query.filter_by(name=name).first()

# --- تعبئة البيانات الأولية (Roles, Permissions, Commands) ---

def seed_all_data():
    with app.app_context():
        db.create_all()

        # Seed Commands
        commands_data = [
            {
                "name": "م1",
                "description": "أوامر الأدمنية",
                "content": """
• أهلاً بك في عزيزي
• أهلاً بك في عزيزي
- قائمة اوامر الادمنيه
━━━━━━━━━━━━ 
- اوامر الرفع والتنزيل :

• رفع - تنزيل مالك اساسي
• رفع - تنزيل مالك
• رفع - تنزيل مشرف
• رفع - تنزيل منشئ
• رفع - تنزيل مدير
• رفع - تنزيل ادمن
• رفع - تنزيل مميز
• تنزيل الكل - لازاله جميع الرتب اعلاه

- اوامر المسح :

• مسح الكل 
• مسح المنشئين
• مسح المدراء
• مسح المالكين
• مسح الادمنيه
• مسح المميزين
• مسح المحظورين
• مسح المكتومين
• مسح قائمه المنع
• مسح الردود
•مسح الاوامر المضافه
• مسح + عدد
• مسح بالرد
• مسح الايدي
• مسح الترحيب
• مسح الرابط


- اوامر الطرد والحظر :

• تقييد + الوقت
• حظر 
• طرد 
• كتم
• تقييد 
• الغاء الحظر 
• الغاء الكتم
• فك التقييد 
• رفع القيود
• منع بالرد
• الغاء منع بالرد
• طرد البوتات
• طرد المحذوفين
• كشف البوتات
━━━━━━━━━━━━
"""
            },
            {
                "name": "م2",
                "description": "أوامر الإعدادات",
                "content": """
اهلا بك في قائمة اوامر الاعدادات :
━━━━━━━━━━━━ 

- اوامر رؤية الاعدادات :

• الرابط
• المالكين
• المالكين الاساسين
• المنشئين 
• الادمنيه
• المدراء
• المميزين
• المحظورين
• القوانين
• المكتومين 
• معلوماتي 
• الحمايه  
• الاعدادت
• المجموعه

- اوامر وضع الاعدادات :

• اضف رابط = بخاص البوت
• مسح الرابط
• انشاء رابط
• ضع الترحيب
• ضع قوانين
• ضـع رابط
• اضف امر
• تعيين الايدي
• اضف قناه (باليوزر ، بالايدي)
• حذف قناه (باليوزر ، بالايدي)

- اوامر التحميل
• تفعيل - تعطيل التحميل
- لليوتيوب
• بحث + اسم الاغنيه
- للتيك توك
• تيك + الرابط
- للساوند
• ساوند + الرابط
━━━━━━━━━━━━
"""
            },
            {
                "name": "م3",
                "description": "أوامر القفل - الفتح",
                "content": """
اهلا بك في قائمة القفل - التعطيل :
- اوامر القفل والفتح :
━━━━━━━━━━━━ 
• قفل - فتح جمثون
• قفل - فتح السب
• قفل - فتح الايرانيه
• قفل - فتح الكتابه
• قفل - فتح الاباحي
• قفل - فتح تعديل الميديا
• قفل - فتح التعديل  
• قفل - فتح الفيديو 
• قفل - فتح الصور 
• قفل - فتح الملصقات 
• قفل - فتح المتحركه 
• قفل - فتح الدردشه 
• قفل - فتح الروابط 
• قفل - فتح التاك 
• قفل - فتح البوتات 
• قفل - فتح المعرفات 
• قفل البوتات بالطرد 
• قفل - فتح الكلايش 
•️ قفل - فتح التكرار 
• قفل - فتح التوجيه 
• قفل - فتح الانلاين 
• قفل - فتح الجهات 
• قفل - فتح الكل 
• قفل - فتح الدخول
• قفل - فتح الصوت
• قفل - فتح التوجيه بالتقييد 
• قفل - فتح الروابط بالتقييد 
• قفل - فتح المتحركه بالتقييد 
• قفل - فتح الصور بالتقييد 
• قفل - فتح الفيديو بالتقييد 
*- اوامر التفعيل - التعطيل :*
• تفعيل - تعطيل ضافني
• تفعيل - تعطيل الاذكار
• تفعيل - تعطيل الثنائي
• تفعيل - تعطيل افتاري 
• تفعيل - تعطيل التسليه 
• تفعيل - تعطيل الكت
• تفعيل - تعطيل الترحيب 
• تفعيل - تعطيل الردود
• تفعيل - تعطيل الانذار 
• تفعيل - تعطيل التحذير 
• تفعيل - تعطيل الايدي
• تفعيل - تعطيل الرابط
• تفعيل - تعطيل اطردني
• تفعيل - تعطيل الحظر
• تفعيل - تعطيل الرفع
• تفعيل - تعطيل التنزيل
• تفعيل - تعطيل التحويل
• تفعيل - تعطيل الحمايه
• تفعيل - تعطيل المنشن
• تفعيل - تعطيل وضع الاقتباسات
• تفعيل - تعطيل الخدميه
• تفعيل - تعطيل اليوتيوب
• تفعيل - تعطيل الايدي بالصوره
• تفعيل - تعطيل التحقق 
• تفعيل - تعطيل ردود السورس 
━━━━━━━━━━━━
"""
            },
            {
                "name": "م4",
                "description": "أوامر التسلية",
                "content": """
• اهلا بك عزيزي
- اوامر التسليه :
━━━━━━━━━━━━
- اوامر تسلية تظهر بالايدي :

• رفع - تنزيل : هطف : الهطوف
• رفع - تنزيل : بثر : البثرين
• رفع - تنزيل : حمار : الحمير
• رفع - تنزيل : كلب : الكلاب
• رفع - تنزيل : كلبه : الكلبات
• رفع - تنزيل : عتوي : العتوين
• رفع - تنزيل : عتويه : العتويات
• رفع - تنزيل : لحجي : اللحوج
• رفع - تنزيل : لحجيه : اللحجيات
• رفع - تنزيل : خروف : الخرفان
• رفع - تنزيل : خفيفه : الخفيفات
• رفع - تنزيل : خفيف : الخفيفين
• رفع بقلبي  : تنزيل من قلبي
━━━━━━━━━━━━
للقروب:
رفع + اسم اختياري 
• مسح رتب التسليه
• رتب التسليه
•تعطيل التسليه
━━━━━━━━━━━━
للعام:
• رفع عام +اسم اختياري
• رتب التسليه عام
• مسح رتب التسليه
━━━━━━━━━━━━
• طلاق - زواج 
• زوجي - زوجتي
• تتزوجني
━━━━━━━━━━━━
•اكتموه (تصويت)
• تعطيل - تفعيل : اكتموه
• تعطيل - تفعيل : زوجني
"""
            },
            {
                "name": "م5",
                "description": "أوامر Dev",
                "content": """
اهلا بك عزيزي Dev
• اضف رد تواصل
• ترحيب البوت
• حذف رد تواصل
• ردود التواصل
• تعطيل
• اسم بوتك + غادر
• تعطيل - تفعيل الزاجل
• مسح المالكين الاساسيين
• مسح صوره الترحيب
• ذيع + ايدي المجموعه - بالرد
• فتح - قفل ردود MY
• رفع - تنزيل Dev = مطور ثانوي
• فتح - قفل الاحصائيات
• فتح - قفل حظر العام
• حظر - كتم عام
• حظر - الغاء حظر بالرد للتواصل
• مسح المحظورين - المحظورين للتواصل
• قائمه العام
• الغاء كتم عام - الغاء عام
• مسح المكتومين عام
• مسح المحظورين عام
• قائمه الرتب العامه 
• تغير الرتب العام
• مسح رتب العام
• مسح رتبه عام
• الردود العامه
• الردود المتعدده العامه 
• مسح الردود العامه 
• مسح الردود المتعدده العامه
• اضف رد عام 
• اضف رد متعدد عام
• اضف ميزة: (صور،صوت،فيديو،فويسات،متحركه)
• اضف لعبه عام(3 العاب كتابيه)
• مسح - ضع كليشه الالعاب
• مسح - ضع كليشه م1
• مسح - ضع كليشه م2
• مسح - ضع كليشه م3
• مسح - ضع كليشه م4
• مسح - ضع كليشه م5
• مسح - ضع كليشه م6
• تحديث
• اعاده تشغيل - reload
"""
            }
        ]

        for cmd_data in commands_data:
            if not Command.query.filter_by(name=cmd_data["name"]).first():
                new_command = Command(name=cmd_data["name"], description=cmd_data["description"], content=cmd_data["content"])
                db.session.add(new_command)
        db.session.commit()

def seed_all_permissions_data():
    with app.app_context():
        # Seed Roles
        roles_data = [
            {"name": "User", "level": 1},
            {"name": "Special", "level": 2},
            {"name": "Admin", "level": 3},
            {"name": "Manager", "level": 4},
            {"name": "Creator", "level": 5},
            {"name": "Supervisor", "level": 6},
            {"name": "Owner", "level": 7},
            {"name": "Dev", "level": 8} # Dev has highest level
        ]
        for role_data in roles_data:
            if not Role.query.filter_by(name=role_data["name"]).first():
                new_role = Role(name=role_data["name"], level=role_data["level"])
                db.session.add(new_role)
        db.session.commit()

        # Seed Permissions
        permissions_data = [
            # Admin Commands
            {"name": "admin_commands", "description": "Access to admin commands"},
            {"name": "manage_ranks", "description": "Ability to promote/demote users"},
            {"name": "clear_data", "description": "Ability to clear various data"},
            {"name": "ban_kick_mute", "description": "Ability to ban, kick, mute users"},

            # Settings Commands
            {"name": "settings_commands", "description": "Access to settings commands"},
            {"name": "view_settings", "description": "Ability to view group settings"},
            {"name": "change_settings", "description": "Ability to change group settings"},
            {"name": "manage_downloads", "description": "Ability to manage download features"},

            # Lock/Unlock Commands
            {"name": "lock_unlock_commands", "description": "Access to lock/unlock commands"},
            {"name": "manage_locks", "description": "Ability to lock/unlock various features"},
            {"name": "manage_activations", "description": "Ability to activate/deactivate features"},

            # Entertainment Commands
            {"name": "entertainment_commands", "description": "Access to entertainment commands"},
            {"name": "manage_fun_ranks", "description": "Ability to manage fun ranks"},
            {"name": "manage_marriage", "description": "Ability to manage marriage game"},
            {"name": "manage_polls", "description": "Ability to manage polls"},

            # Dev Commands
            {"name": "dev_commands", "description": "Access to developer commands"},
            {"name": "manage_responses", "description": "Ability to manage bot responses"},
            {"name": "manage_bot_status", "description": "Ability to manage bot status (leave, restart)"},
            {"name": "manage_global_bans", "description": "Ability to manage global bans/mutes"},
            {"name": "manage_global_ranks", "description": "Ability to manage global ranks"},
            {"name": "manage_global_responses", "description": "Ability to manage global responses"},
            {"name": "manage_features", "description": "Ability to add/remove bot features"},
            {"name": "manage_games", "description": "Ability to manage bot games"},
            {"name": "update_bot", "description": "Ability to update/restart the bot"},

            # General Permissions
            {"name": "use_bot", "description": "Basic ability to interact with the bot"},
            {"name": "view_rank", "description": "Ability to view own and others rank"}
        ]
        for perm_data in permissions_data:
            if not Permission.query.filter_by(name=perm_data["name"]).first():
                new_perm = Permission(name=perm_data["name"], description=perm_data["description"])
                db.session.add(new_perm)
        db.session.commit()

        # Assign Permissions to Roles
        role_permissions_map = {
            "User": ["use_bot", "view_rank"],
            "Special": ["use_bot", "view_rank", "entertainment_commands"],
            "Admin": ["use_bot", "view_rank", "entertainment_commands", "admin_commands", "settings_commands", "lock_unlock_commands"],
            "Manager": ["use_bot", "view_rank", "entertainment_commands", "admin_commands", "settings_commands", "lock_unlock_commands", "manage_ranks", "manage_locks"],
            "Creator": ["use_bot", "view_rank", "entertainment_commands", "admin_commands", "settings_commands", "lock_unlock_commands", "manage_ranks", "manage_locks", "manage_activations", "manage_downloads"],
            "Supervisor": ["use_bot", "view_rank", "entertainment_commands", "admin_commands", "settings_commands", "lock_unlock_commands", "manage_ranks", "manage_locks", "manage_activations", "manage_downloads", "clear_data", "ban_kick_mute", "change_settings"],
            "Owner": [
                "use_bot", "view_rank", "entertainment_commands", "admin_commands", "settings_commands", 
                "lock_unlock_commands", "manage_ranks", "manage_locks", "manage_activations", 
                "manage_downloads", "clear_data", "ban_kick_mute", "change_settings", "manage_fun_ranks", 
                "manage_marriage", "manage_polls", "manage_responses", "manage_bot_status", 
                "manage_global_bans", "manage_global_ranks", "manage_global_responses", 
                "manage_features", "manage_games", "update_bot", "dev_commands" # Owner has all permissions except Dev specific ones
            ],
            "Dev": [
                "use_bot", "view_rank", "entertainment_commands", "admin_commands", "settings_commands", 
                "lock_unlock_commands", "manage_ranks", "manage_locks", "manage_activations", 
                "manage_downloads", "clear_data", "ban_kick_mute", "change_settings", "manage_fun_ranks", 
                "manage_marriage", "manage_polls", "manage_responses", "manage_bot_status", 
                "manage_global_bans", "manage_global_ranks", "manage_global_responses", 
                "manage_features", "manage_games", "update_bot", "dev_commands" # Dev has all permissions
            ]
        }

        for role_name, perms in role_permissions_map.items():
            role = Role.query.filter_by(name=role_name).first()
            if role:
                for perm_name in perms:
                    permission = Permission.query.filter_by(name=perm_name).first()
                    if permission:
                        if not RolePermission.query.filter_by(role_id=role.id, permission_id=permission.id).first():
                            db.session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.session.commit()

        # Assign Owner to the initial user
        owner_user = User.query.filter_by(telegram_id=OWNER_USER_ID).first()
        if owner_user:
            dev_role = Role.query.filter_by(name="Dev").first()
            if dev_role:
                owner_user.role = dev_role
                db.session.commit()
                logger.info(f"Assigned Dev role to owner: {owner_user.username or owner_user.first_name}")

# --- وظائف البوت (Telegram Handlers) ---

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name

        user = User.query.filter_by(telegram_id=user_id).first()
        if not user:
            user = User(telegram_id=user_id, username=username, first_name=first_name, last_name=last_name)
            db.session.add(user)
            db.session.commit()
            logger.info(f"New user added: {user_id}")
        else:
            # Update user info in case it changed
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            db.session.commit()

    await update.message.reply_text(
        f"أهلاً بك عزيزي {first_name or username} في بوت الأوامر!\n" 
        "يمكنك كتابة /اوامر لعرض قائمة الأوامر الرئيسية."
    )

        async def show_main_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not has_permission(user_id, "use_bot"):
            await update.message.reply_text("عذراً، ليس لديك الصلاحية لاستخدام هذا الأمر.")
            return

        keyboard = [
            [InlineKeyboardButton("أوامر الأدمنية (م1)", callback_data="m1")],
            [InlineKeyboardButton("أوامر الإعدادات (م2)", callback_data="m2")],
            [InlineKeyboardButton("أوامر القفل - الفتح (م3)", callback_data="m3")],
            [InlineKeyboardButton("أوامر التسلية (م4)", callback_data="m4")],
            [InlineKeyboardButton("أوامر Dev (م5)", callback_data="m5")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("أهلاً بك عزيزي في قائمة الأوامر:", reply_markup=reply_markup)

        await update.message.reply_text(
            "أهلاً بك عزيزي في قائمة الاوامر :\n" 
            "━━━━━━━━━━━━\n" 
            "◂ م1 : اوامر الادمنيه\n" 
            "◂ م2 : اوامر الاعدادات\n" 
            "◂ م3 : اوامر القفل - الفتح\n" 
            "◂ م4 : اوامر التسليه\n" 
            "◂ م5 : اوامر Dev\n" 
            "━━━━━━━━━━━━",
            reply_markup=reply_markup
        )

        async def handle_command_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if query.data == "main_menu":
            await self.show_main_commands(update, context)
            return

        command_name = query.data
        command_entry = Command.query.filter_by(name=command_name).first()

        if not command_entry:
            await query.edit_message_text("عذراً، هذا الأمر غير موجود.")
            return

        # Check permissions based on command category
        permission_map = {
            "m1": "admin_commands",
            "m2": "settings_commands",
            "m3": "lock_unlock_commands",
            "m4": "entertainment_commands",
            "m5": "dev_commands",
        }
        required_permission = permission_map.get(command_name)
        user_id = update.effective_user.id
        if required_permission and not has_permission(user_id, required_permission):
            await query.edit_message_text("عذراً، ليس لديك الصلاحية لعرض أوامر هذه الفئة.")
            return

        keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(command_entry.content, reply_markup=reply_markup)

        async def handle_text_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = update.message.text.strip()

        if text.lower() == "اوامر":
            await self.show_main_commands(update, context)
            return
        
        command_entry = Command.query.filter_by(name=text.lower()).first()
        if command_entry:
            # Check permissions based on command category
            permission_map = {
                "m1": "admin_commands",
                "m2": "settings_commands",
                "m3": "lock_unlock_commands",
                "m4": "entertainment_commands",
                "m5": "dev_commands",
            }
            required_permission = permission_map.get(text.lower())

            user_id = update.effective_user.id
            if required_permission and not has_permission(user_id, required_permission):
                await update.message.reply_text("عذراً، ليس لديك الصلاحية لعرض أوامر هذه الفئة.")
                return

            await update.message.reply_text(command_entry.content)
            return

    # If it's not a recognized command, do nothing (silent bot)
    # await update.message.reply_text("عذراً، لا أفهم هذا الأمر. يرجى استخدام /اوامر أو الأوامر المحددة.")

    async def get_my_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        user_info = update.effective_user

        if not has_permission(user_id, "view_rank"):
            await update.message.reply_text("عذراً، ليس لديك الصلاحية لعرض الرتب.")
            return

        user = User.query.filter_by(telegram_id=user_id).first()
        if not user:
            user = User(telegram_id=user_id, username=user_info.username, first_name=user_info.first_name, last_name=user_info.last_name)
            db.session.add(user)
            db.session.commit()
            user_role = Role.query.filter_by(name="User").first()
        else:
            user_role = user.role

        role_name = user_role.name if user_role else "User"
        is_owner = " (مالك البوت الأساسي)" if user_id == OWNER_USER_ID else ""

        await update.message.reply_text(
            f"معلومات رتبتك:\n"
            f"الاسم: {user_info.first_name or user_info.username}\n"
            f"المعرف: @{user_info.username or 'لا يوجد'}\n"
            f"الرتبة: {role_name}{is_owner}"
        )

    async def get_other_rank(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id

        if not has_permission(user_id, "view_rank"):
            await update.message.reply_text("عذراً، ليس لديك الصلاحية لعرض الرتب.")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("يرجى الرد على رسالة الشخص الذي تريد معرفة رتبته.")
            return

        target_user_id = update.message.reply_to_message.from_user.id
        target_username = update.message.reply_to_message.from_user.username
        target_first_name = update.message.reply_to_message.from_user.first_name

        target_user = User.query.filter_by(telegram_id=target_user_id).first()
        if not target_user:
            target_user = User(telegram_id=target_user_id, username=target_username, first_name=target_first_name)
            db.session.add(target_user)
            db.session.commit()
            target_user_role = Role.query.filter_by(name="User").first()
        else:
            target_user_role = target_user.role

        role_name = target_user_role.name if target_user_role else "User"
        is_owner = " (مالك البوت الأساسي)" if target_user_id == OWNER_USER_ID else ""

        await update.message.reply_text(
            f"معلومات رتبة {target_first_name or target_username}:\n"
            f"الاسم: {target_first_name or target_username}\n"
            f"المعرف: @{target_username or 'لا يوجد'}\n"
            f"الرتبة: {role_name}{is_owner}"
        )
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"حدث خطأ: {context.error}", exc_info=context.error)
        if update and update.effective_message:
            await update.effective_message.reply_text("عذراً، حدث خطأ ما. يرجى المحاولة مرة أخرى لاحقاً.")
        else:
            logger.error("حدث خطأ غير متوقع ولم يتمكن البوت من إرسال رسالة للمستخدم.")

# --- وظائف الإدارة (Admin Commands) ---

    async def promote_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        if not has_permission(user_id, "manage_ranks"):
            await update.message.reply_text("عذراً، ليس لديك الصلاحية لترقية الرتب.")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("يرجى الرد على رسالة المستخدم الذي تريد ترقيته.")
            return

        target_user_id = update.message.reply_to_message.from_user.id
        target_first_name = update.message.reply_to_message.from_user.first_name

        if target_user_id == OWNER_USER_ID and user_id != OWNER_USER_ID:
            await update.message.reply_text("لا يمكنك ترقية مالك البوت الأساسي.")
            return

        target_user = User.query.filter_by(telegram_id=target_user_id).first()
        if not target_user:
            await update.message.reply_text("المستخدم غير مسجل في البوت. يرجى الطلب منه التفاعل مع البوت أولاً.")
            return

        current_role_level = target_user.role.level if target_user.role else 1
        next_role = get_role_by_level(current_role_level + 1)

        if not next_role:
            await update.message.reply_text(f"المستخدم {target_first_name} لديه أعلى رتبة ممكنة بالفعل.")
            return
        
        # Prevent promoting above your own level unless you are the owner
        if user_id != OWNER_USER_ID:
            promoter_role = get_user_role(user_id)
            if promoter_role.level <= next_role.level:
                await update.message.reply_text("لا يمكنك ترقية مستخدم إلى رتبة أعلى من رتبتك أو مساوية لها.")
                return

        target_user.role = next_role
        db.session.commit()
        await update.message.reply_text(f"تم ترقية {target_first_name} إلى رتبة {next_role.name} بنجاح.")

    async def demote_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        if not has_permission(user_id, "manage_ranks"):
            await update.message.reply_text("عذراً، ليس لديك الصلاحية لتنزيل الرتب.")
            return

        if not update.message.reply_to_message:
            await update.message.reply_text("يرجى الرد على رسالة المستخدم الذي تريد تنزيل رتبته.")
            return

        target_user_id = update.message.reply_to_message.from_user.id
        target_first_name = update.message.reply_to_message.from_user.first_name

        if target_user_id == OWNER_USER_ID and user_id != OWNER_USER_ID:
            await update.message.reply_text("لا يمكنك تنزيل مالك البوت الأساسي.")
            return

        target_user = User.query.filter_by(telegram_id=target_user_id).first()
        if not target_user:
            await update.message.reply_text("المستخدم غير مسجل في البوت. يرجى الطلب منه التفاعل مع البوت أولاً.")
            return

        current_role_level = target_user.role.level if target_user.role else 1
        previous_role = get_role_by_level(current_role_level - 1)

        if not previous_role:
            await update.message.reply_text(f"المستخدم {target_first_name} لديه أدنى رتبة ممكنة بالفعل.")
            return

        # Prevent demoting below your own level unless you are the owner
        if user_id != OWNER_USER_ID:
            demoter_role = get_user_role(user_id)
            if demoter_role.level <= previous_role.level:
                await update.message.reply_text("لا يمكنك تنزيل مستخدم إلى رتبة أدنى من رتبتك أو مساوية لها.")
                return

        target_user.role = previous_role
        db.session.commit()
        await update.message.reply_text(f"تم تنزيل {target_first_name} إلى رتبة {previous_role.name} بنجاح.")

    async def set_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id
        if not has_permission(user_id, "manage_ranks"):
            await update.message.reply_text("عذراً، ليس لديك الصلاحية لتعيين الرتب.")
            return

        if not update.message.reply_to_message or not context.args:
            await update.message.reply_text("يرجى الرد على رسالة المستخدم وتحديد الرتبة الجديدة. مثال: /set_role Admin")
            return

        target_user_id = update.message.reply_to_message.from_user.id
        target_first_name = update.message.reply_to_message.from_user.first_name
        new_role_name = context.args[0].capitalize() # Capitalize first letter for role name

        if target_user_id == OWNER_USER_ID and user_id != OWNER_USER_ID:
            await update.message.reply_text("لا يمكنك تغيير رتبة مالك البوت الأساسي.")
            return

        target_user = User.query.filter_by(telegram_id=target_user_id).first()
        if not target_user:
            await update.message.reply_text("المستخدم غير مسجل في البوت. يرجى الطلب منه التفاعل مع البوت أولاً.")
            return

        new_role = get_role_by_name(new_role_name)
        if not new_role:
            await update.message.reply_text(f"الرتبة \'{new_role_name}\' غير موجودة. الرتب المتاحة: User, Special, Admin, Manager, Creator, Supervisor, Owner, Dev.")
            return
        
        # Prevent setting role above your own level unless you are the owner
        if user_id != OWNER_USER_ID:
            setter_role = get_user_role(user_id)
            if setter_role.level <= new_role.level and new_role.name != target_user.role.name:
                await update.message.reply_text("لا يمكنك تعيين رتبة أعلى من رتبتك أو مساوية لها.")
                return

        target_user.role = new_role
        db.session.commit()
        await update.message.reply_text(f"تم تعيين رتبة {new_role.name} للمستخدم {target_first_name} بنجاح.")

# --- وظيفة تشغيل البوت ---

class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("اوامر", self.show_main_commands))
        self.application.add_handler(CallbackQueryHandler(self.handle_command_query))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^(م1|م2|م3|م4|م5|اوامر|رتبتي|رتبته|رفع|تنزيل|ضع_رتبه)$'), self.handle_text_commands))
        self.application.add_handler(CommandHandler("رتبتي", self.get_my_rank))
        self.application.add_handler(CommandHandler("رتبته", self.get_other_rank))
        self.application.add_handler(CommandHandler("رفع", self.promote_user))
        self.application.add_handler(CommandHandler("تنزيل", self.demote_user))
        self.application.add_handler(CommandHandler("ضع_رتبه", self.set_role))

        # Error handler
        self.application.add_error_handler(self.error_handler)
        # Error handler


    def run(self):
        # Ensure database and seed data are created when bot starts
        with app.app_context():
            db.create_all()
            seed_all_data()
            seed_all_permissions_data()
            logger.info("Database seeded successfully.")

        # For local testing, use polling
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)



if __name__ == "__main__":
    # Create database directory if it doesn't exist
    os.makedirs("database", exist_ok=True)

    # Initialize and run the bot
    bot = TelegramBot()
    bot.run()
