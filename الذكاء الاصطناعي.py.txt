import os
import logging
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from datetime import datetime, timedelta

# إعدادات البوت (تم تضمينها مباشرة بناءً على طلبك)
BOT_TOKEN = "8069419306:AAEWY3K3kvanMqAKrQegyh9gKOHM_orFO20"
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
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), default=1) # Default to User role
    role = db.relationship('Role', backref='users')

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
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'), primary_key=True)

    role = db.relationship('Role', backref=db.backref('role_permissions', lazy=True))
    permission = db.relationship('Permission', backref=db.backref('permission_roles', lazy=True))

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
    try:
        user = User.query.filter_by(telegram_id=telegram_id).first()
        if user and user.role:
            return user.role
        return Role.query.filter_by(name='User').first()  # Default to User role if not found
    except Exception as e:
        logger.error(f"Error fetching user role: {e}")
        return None

def has_permission(telegram_id, permission_name):
    try:
        role = get_user_role(telegram_id)
        if not role:
            return False
        
        # Owner and Dev roles have all permissions
        if role.name in ['Owner', 'Dev']:
            return True

        permission = Permission.query.filter_by(name=permission_name).first()
        if not permission:
            return False
        
        return RolePermission.query.filter_by(role_id=role.id, permission_id=permission.id).first() is not None
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        return False

def get_role_by_level(level):
    try:
        return Role.query.filter_by(level=level).first()
    except Exception as e:
        logger.error(f"Error fetching role by level {level}: {e}")
        return None

def get_role_by_name(name):
    try:
        return Role.query.filter_by(name=name).first()
    except Exception as e:
        logger.error(f"Error fetching role by name {name}: {e}")
        return None

# --- تعبئة البيانات الأولية (Roles, Permissions, Commands) ---

def seed_all_data():
    try:
        with app.app_context():
            db.create_all()

            # Seed Commands
            commands_data = [
                {
                    "name": "م1",
                    "description": "أوامر الأدمنية",
                    "content": """...""",
                },
                {
                    "name": "م2",
                    "description": "أوامر الإعدادات",
                    "content": """...""",
                },
                {
                    "name": "م3",
                    "description": "أوامر القفل - الفتح",
                    "content": """...""",
                },
                {
                    "name": "م4",
                    "description": "أوامر التسليه",
                    "content": """...""",
                },
                {
                    "name": "م5",
                    "description": "أوامر Dev",
                    "content": """...""",
                },
            ]

            for cmd_data in commands_data:
                if not Command.query.filter_by(name=cmd_data['name']).first():
                    new_command = Command(name=cmd_data['name'], description=cmd_data['description'], content=cmd_data['content'])
                    db.session.add(new_command)
            db.session.commit()
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        db.session.rollback()

def seed_all_permissions_data():
    try:
        with app.app_context():
            # Seed Roles
            roles_data = [
                {'name': 'User', 'level': 1},
                {'name': 'Special', 'level': 2},
                {'name': 'Admin', 'level': 3},
                {'name': 'Manager', 'level': 4},
                {'name': 'Creator', 'level': 5},
                {'name': 'Supervisor', 'level': 6},
                {'name': 'Owner', 'level': 7},
                {'name': 'Dev', 'level': 8} # Dev has highest level
            ]
            for role_data in roles_data:
                if not Role.query.filter_by(name=role_data['name']).first():
                    new_role = Role(name=role_data['name'], level=role_data['level'])
                    db.session.add(new_role)
            db.session.commit()

            # Seed Permissions
            permissions_data = [
                {'name': 'admin_commands', 'description': 'Access to admin commands'},
                {'name': 'manage_ranks', 'description': 'Ability to promote/demote users'},
                {'name': 'clear_data', 'description': 'Ability to clear various data'},
                {'name': 'ban_kick_mute', 'description': 'Ability to ban, kick, mute users'},
                # Add more permissions as needed...
            ]
            for perm_data in permissions_data:
                if not Permission.query.filter_by(name=perm_data['name']).first():
                    new_perm = Permission(name=perm_data['name'], description=perm_data['description'])
                    db.session.add(new_perm)
            db.session.commit()

            # Assign Permissions to Roles
            role_permissions_map = {
                'User': ['use_bot', 'view_rank'],
                'Special': ['use_bot', 'view_rank', 'entertainment_commands'],
                'Admin': ['use_bot', 'view_rank', 'admin_commands'],
                # Add other roles and permissions
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
                dev_role = Role.query.filter_by(name='Dev').first()
                if dev_role:
                    owner_user.role = dev_role
                    db.session.commit()
                    logger.info(f"Assigned Dev role to owner: {owner_user.username or owner_user.first_name}")
            else:
                logger.warning(f"Owner user with ID {OWNER_USER_ID} not found during seeding.")
    except Exception as e:
        logger.error(f"Error seeding permissions and roles: {e}")
        db.session.rollback()

# --- وظائف البوت (Telegram Handlers) ---

async def start(update: Update, context: Application.Context) -> None:
    try:
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
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            db.session.commit()

        await update.message.reply_text(
            f"أهلاً بك عزيزي {first_name or username} في بوت الأوامر!\n" 
            "يمكنك كتابة /اوامر لعرض قائمة الأوامر الرئيسية."
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("عذراً، حدث خطأ أثناء بدء البوت.")
