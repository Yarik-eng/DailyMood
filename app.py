"""
DailyMood Flask Application

This module defines a Flask app with helper functions for database initialization
and routes for the small DailyMood app. Routes are intentionally simple and return
either HTML templates or JSON for frontend handling. Key helpers are:
- test_db_connection(): Quick test of database connectivity
- create_tables(): Initializes SQLAlchemy models

Routes include:
- /, /about, /favorites, /journal, /goals, /statistics (template renders)
- /api/journal (GET/POST) and /api/journal/<id> (PUT/DELETE) for entries

The code below uses SQLAlchemy models defined in `models.py` (MoodEntry).
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_session import Session
from flasgger import Swagger, swag_from
from functools import wraps
import time
import os
import logging
import json
from datetime import datetime, timedelta
from sqlalchemy import func, extract, inspect, text
from models import db, MoodEntry, Feedback, User, Product, Order, OrderItem, Payment
from habits_models import Habit, HabitCompletion, MonthlyGoal
from marshmallow import ValidationError
from schemas import (
    ma, products_schema, create_order_schema, order_output_schema,
    create_payment_schema, payment_output_schema, create_feedback_schema,
    feedback_output_schema, feedbacks_schema, create_journal_entry_schema,
    journal_entry_output_schema
)
import traceback
import io
import csv

# Налаштування логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

AVAILABLE_AVATARS = [
    'cat',
    'dog',
    'bunny',
    'bear',
    'koala',
    'bee',
    'penguin',
    'frog',
    'mushroom',
    'star',
    'cactus'
]

PREMIUM_AVATARS = ['unicorn', 'dragon', 'koi', 'phoenix', 'crown', 'crystal', 'moon', 'butterfly']

app.config['AVAILABLE_AVATARS'] = AVAILABLE_AVATARS

# Configure database: prefer env `DATABASE_URL` (PostgreSQL in production), fallback to SQLite file
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'data', 'dailymood.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Use DATABASE_URL or SQLALCHEMY_DATABASE_URI if provided, otherwise SQLite
env_db_url = os.environ.get('DATABASE_URL') or os.environ.get('SQLALCHEMY_DATABASE_URI')
if env_db_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = env_db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Секретний ключ для сесій (в продакшені використовуйте змінну середовища)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Конфігурація сесії та cookies — зчитуємо з оточення, ставимо безпечні значення за замовчуванням
def _str_to_bool(v, default=False):
    if v is None:
        return default
    return str(v).lower() in ('1', 'true', 'yes', 'on')

# Рекомендується встановлювати у .env.production або в Railway Variables
app.config['SESSION_COOKIE_SECURE'] = _str_to_bool(os.environ.get('SESSION_COOKIE_SECURE'), default=(os.environ.get('FLASK_ENV') == 'production'))
app.config['SESSION_COOKIE_HTTPONLY'] = _str_to_bool(os.environ.get('SESSION_COOKIE_HTTPONLY'), default=True)
# SESSION_COOKIE_SAMESITE: 'Lax', 'Strict', or 'None' (None -> browser default / unset)
_samesite = os.environ.get('SESSION_COOKIE_SAMESITE')
if _samesite is None:
    # production default: Lax, development: None (to allow flexible testing)
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' if os.environ.get('FLASK_ENV') == 'production' else None
else:
    # allow explicit 'None' value to mean None (not the string)
    if str(_samesite).lower() in ('none', 'null'):
        app.config['SESSION_COOKIE_SAMESITE'] = None
    else:
        app.config['SESSION_COOKIE_SAMESITE'] = str(_samesite)

try:
    app.config['PERMANENT_SESSION_LIFETIME'] = int(os.environ.get('PERMANENT_SESSION_LIFETIME', 2592000))
except Exception:
    app.config['PERMANENT_SESSION_LIFETIME'] = 2592000

# Конфігурація постійного збереження сесій на диск
session_dir = os.path.join(basedir, 'data', 'sessions')
os.makedirs(session_dir, exist_ok=True)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_FILE_DIR'] = session_dir

# Ініціалізація бази даних
db.init_app(app)
# Ініціалізація постійної сесії (filesystem)
Session(app)

# Health check endpoint for container orchestration
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

# Ініціалізація Marshmallow для валідації
ma.init_app(app)

# Ініціалізація Swagger для API документації
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "DailyMood API",
        "description": "REST API для додатку DailyMood - щоденник настрою, звичок та цілей",
        "version": "1.0.0",
        "contact": {
            "name": "DailyMood Team",
            "email": "support@dailymood.app"
        }
    },
    "host": "localhost:5000",
    "basePath": "/",
    "schemes": ["http"],
    "securityDefinitions": {
        "SessionAuth": {
            "type": "apiKey",
            "name": "session",
            "in": "cookie",
            "description": "Flask session cookie для авторизації"
        }
    }
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Реєстрація API Blueprints для версіювання
from api_blueprints import api_v1, api_v2
app.register_blueprint(api_v1)
app.register_blueprint(api_v2)


# -------------------- Helper функції --------------------
def validate_request_data(schema, data=None):
    """
    Валідує вхідні дані за допомогою Marshmallow схеми
    
    Args:
        schema: Marshmallow схема для валідації
        data: Дані для валідації (якщо None, береться request.get_json())
    
    Returns:
        tuple: (validated_data, errors) або (None, error_response)
    """
    if data is None:
        data = request.get_json()
    
    if not data:
        return None, (jsonify({'status': 'error', 'message': 'Відсутні дані в запиті'}), 400)
    
    try:
        validated_data = schema.load(data)
        return validated_data, None
    except ValidationError as err:
        return None, (jsonify({
            'status': 'error',
            'message': 'Помилка валідації',
            'errors': err.messages
        }), 400)


# -------------------- Декоратори авторизації --------------------
def login_required(f):
    """Декоратор для захисту роутів - вимагає входу."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Для API-роутів повертаємо 401 JSON
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'status': 'error', 'message': 'Потрібна авторизація'}), 401
            # Для HTML-сторінок — редірект на сторінку входу
            next_url = request.path
            return redirect(url_for('login') + f"?next={next_url}")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Декоратор для адмін-роутів - вимагає is_admin=True."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Потрібна авторизація'}), 401
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'status': 'error', 'message': 'Доступ заборонено'}), 403
        return f(*args, **kwargs)
    return decorated_function


def ensure_admin_presence(candidate_user: User) -> None:
    """Гарантує, що принаймні один адміністратор існує.

    Якщо в таблиці користувачів ще немає запису з is_admin=True, наданий
    користувач отримує адмін-права. Зміни одразу комітяться, бо функція може
    викликатись і під час логіну, і при реєстрації нового користувача.
    """
    try:
        if not User.query.filter_by(is_admin=True).first():
            candidate_user.is_admin = True
            db.session.commit()
            logging.info("Призначено адміністратора: %s", candidate_user.email)
    except Exception as exc:
        logging.error("Помилка під час призначення адміністратора: %s", exc)
        db.session.rollback()


@app.context_processor
def inject_static_version():
    """Provide a static_version value (file mtime or server start time) to use as a cache-buster in templates."""
    try:
        static_path = os.path.join(basedir, 'static', 'style.css')
        v = int(os.path.getmtime(static_path))
    except Exception:
        v = int(time.time())
    return dict(static_version=v)

def test_db_connection():
    """Перевірка з'єднання з базою даних.

    Attempts to open a connection to the configured SQLAlchemy engine.
    Returns True when successful, False otherwise. This is a lightweight
    smoke-test used before starting the server in development.
    """
    try:
        with app.app_context():
            db.engine.connect()
            logging.info("Database connection successful")
            return True
    except Exception as e:
        logging.error(f"Database connection failed: {str(e)}")
        return False

def create_tables():
    """Create database tables if they don't exist.

    Uses SQLAlchemy's metadata to create any missing tables. This is safe
    to call on application startup and will be skipped if tables already
    exist. Any exceptions are logged and re-raised to make failures visible.
    """
    try:
        with app.app_context():
            db.create_all()
            logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating database tables: {str(e)}")
        raise

# Переконуємось що таблиці існують при імпорті/запуску для розробки
def ensure_user_avatar_column():
    """Додає колонку avatar до таблиці users, якщо її ще немає."""
    try:
        inspector = inspect(db.engine)
        columns = {col['name'] for col in inspector.get_columns('users')}
        if 'avatar' not in columns:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN avatar VARCHAR(255)'))
            logging.info("Додано колонку avatar до таблиці users")
    except Exception as exc:
        logging.error("Не вдалося гарантувати наявність avatar у users: %s", exc)


def ensure_user_premium_columns():
    """Додає колонки для преміум-статусу, якщо їх немає."""
    try:
        inspector = inspect(db.engine)
        columns = {col['name'] for col in inspector.get_columns('users')}
        alterations = []
        if 'is_premium' not in columns:
            alterations.append('ADD COLUMN is_premium BOOLEAN NOT NULL DEFAULT 0')
        if 'premium_started_at' not in columns:
            alterations.append('ADD COLUMN premium_started_at DATETIME')
        if 'premium_expires_at' not in columns:
            alterations.append('ADD COLUMN premium_expires_at DATETIME')
        if alterations:
            with db.engine.connect() as conn:
                for statement in alterations:
                    conn.execute(text(f'ALTER TABLE users {statement}'))
            logging.info("Гарантовано наявність колонок преміум у таблиці users")
    except Exception as exc:
        logging.error("Не вдалося гарантувати наявність колонок преміум у users: %s", exc)


def ensure_user_advice_unlock_column():
    """Додає колонку advice_unlock_once для одноразового скидання блокування поради."""
    try:
        inspector = inspect(db.engine)
        columns = {col['name'] for col in inspector.get_columns('users')}
        if 'advice_unlock_once' not in columns:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE users ADD COLUMN advice_unlock_once BOOLEAN NOT NULL DEFAULT 0'))
            logging.info("Додано колонку advice_unlock_once до таблиці users")
    except Exception as exc:
        logging.error("Не вдалося гарантувати наявність advice_unlock_once у users: %s", exc)


def ensure_mood_entry_user_id():
    """Додає колонку user_id до mood_entries, якщо її немає."""
    try:
        inspector = inspect(db.engine)
        columns = {col['name'] for col in inspector.get_columns('mood_entries')}
        if 'user_id' not in columns:
            # Спочатку додаємо колонку як nullable
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE mood_entries ADD COLUMN user_id INTEGER'))
                conn.commit()
            logging.info("Додано колонку user_id до таблиці mood_entries")
            
            # Якщо є існуючі записи без user_id, видаляємо їх або присвоюємо першому користувачу
            with db.engine.connect() as conn:
                result = conn.execute(text('SELECT COUNT(*) as cnt FROM mood_entries WHERE user_id IS NULL'))
                orphan_count = result.fetchone()[0]
                if orphan_count > 0:
                    # Присвоюємо першому користувачу
                    first_user = conn.execute(text('SELECT id FROM users ORDER BY id LIMIT 1')).fetchone()
                    if first_user:
                        conn.execute(text(f'UPDATE mood_entries SET user_id = {first_user[0]} WHERE user_id IS NULL'))
                        logging.info(f"Присвоєно {orphan_count} старих записів користувачу #{first_user[0]}")
                    else:
                        # Немає користувачів — видаляємо старі записи
                        conn.execute(text('DELETE FROM mood_entries WHERE user_id IS NULL'))
                        logging.info(f"Видалено {orphan_count} старих записів без користувачів")
                    conn.commit()
    except Exception as exc:
        logging.error("Не вдалося гарантувати наявність user_id у mood_entries: %s", exc)


def ensure_habit_user_column():
    """Додає колонку user_id до таблиці habits, якщо її немає."""
    try:
        inspector = inspect(db.engine)
        if 'habits' in inspector.get_table_names():
            columns = {col['name'] for col in inspector.get_columns('habits')}
            if 'user_id' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE habits ADD COLUMN user_id INTEGER'))
                logging.info('Додано колонку user_id до таблиці habits')
    except Exception as exc:
        logging.error('Не вдалося додати колонку user_id у habits: %s', exc)


def ensure_goal_user_column():
    """Додає колонку user_id до таблиці monthly_goals, якщо її немає."""
    try:
        inspector = inspect(db.engine)
        if 'monthly_goals' in inspector.get_table_names():
            columns = {col['name'] for col in inspector.get_columns('monthly_goals')}
            if 'user_id' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE monthly_goals ADD COLUMN user_id INTEGER'))
                logging.info('Додано колонку user_id до таблиці monthly_goals')
    except Exception as exc:
        logging.error('Не вдалося додати колонку user_id у monthly_goals: %s', exc)


with app.app_context():
    db.create_all()
    # Виконуємо допоміжні ALTER-и лише для SQLite (локальні оновлення схеми)
    try:
        if db.engine.dialect.name == 'sqlite':
            ensure_user_avatar_column()
            ensure_user_premium_columns()
            ensure_user_advice_unlock_column()
            ensure_mood_entry_user_id()
            ensure_habit_user_column()
            ensure_goal_user_column()
        else:
            logging.info("Skipping SQLite-specific schema helpers for %s", db.engine.dialect.name)
    except Exception:
        logging.exception("Failed running schema helpers")

@app.errorhandler(404)
def not_found_error(error):
    logging.warning(f"404 error: {request.url}")
    return jsonify({
        'status': 'error',
        'message': 'Requested resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    # Логуємо повний traceback для діагностики несподіваних помилок сервера
    try:
        tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    except Exception:
        tb = str(error)
    logging.error(f"500 error: {str(error)}\n{tb}")
    # Відкочуємо будь-яку активну транзакцію БД щоб зберегти сесію чистою
    try:
        db.session.rollback()
    except Exception:
        logging.exception('Failed to rollback DB session after 500')

    return jsonify({
        'status': 'error',
        'message': 'Internal server error occurred'
    }), 500

@app.before_request
def before_request():
    """Log each request and set up user context."""
    logging.info(f"Request: {request.method} {request.url}")
    
    # Встановлюємо поточного користувача для використання у шаблонах
    if 'user_id' in session:
        from flask import g
        g.user = User.query.get(session['user_id'])
    else:
        from flask import g
        g.user = None

@app.after_request
def after_request(response):
    """Add headers to allow cookies and CORS."""
    # Дозволяємо cookies при запитах з того ж домену
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    
    # Додаємо явне вказання браузеру зберігати cookies
    logging.debug(f"Response: {response.status} for {request.path}")
    return response

@app.route('/')
def index():
    advice_unlock_once = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            advice_unlock_once = user.advice_unlock_once
            # Reset the flag if it was used
            if advice_unlock_once:
                user.advice_unlock_once = False
                db.session.commit()
    return render_template('index.html', advice_unlock_once=advice_unlock_once)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/lab6')
def lab6_demo():
    """Проста сторінка для лабораторної №6 з формою та списком ресурсів."""
    return render_template('lab6_feedback.html')

@app.route('/favorites')
def favorites():
    return render_template('favorites.html')

@app.route('/journal')
def journal():
    """Сторінка щоденника."""
    return render_template('journal.html')

@app.route('/goals')
def goals():
    """Сторінка цілей."""
    return render_template('goals.html')

@app.route('/store')
def store():
    """Публічна сторінка магазину wellness-продуктів."""
    return render_template('store.html')

@app.route('/checkout')
@login_required
def checkout_page():
    """Сторінка оформлення замовлення та оплати."""
    return render_template('checkout.html')

@app.route('/profile')
@login_required
def profile_page():
    """Профіль користувача зі списком останніх активностей."""
    return render_template('profile.html')

@app.route('/statistics')
@login_required
def statistics():
    """Render statistics page with recent mood analytics.

    Prepares a small summary (count, most common mood) and a dataset used
    by the frontend Chart.js to render trend and distribution charts.
    The function returns a rendered template with the following context:
    - monthly_entries: int
    - most_common_mood: str
    - mood_data: dict containing dates, values and counts
    """
    user_id = session.get('user_id')
    lang = request.args.get('lang', 'uk')  # Get language from URL param or default to uk
    
    # Отримуємо дані за останній місяць — порівнюємо по date() бо MoodEntry.date це Date
    month_ago = (datetime.utcnow() - timedelta(days=30)).date()
    
    # Кількість записів за місяць (тільки для поточного користувача)
    monthly_entries = MoodEntry.query.filter(
        MoodEntry.user_id == user_id,
        MoodEntry.date >= month_ago
    ).count()

    # Найчастіший настрій (тільки для поточного користувача)
    most_common = db.session.query(
        MoodEntry.mood,
        func.count(MoodEntry.mood).label('count')
    ).filter(
        MoodEntry.user_id == user_id
    ).group_by(MoodEntry.mood).order_by(
        func.count(MoodEntry.mood).desc()
    ).first()
    raw_most_common = most_common.mood if most_common else None

    # Допоміжна функція: перекладаємо внутрішні ключі настрою на мітки для відображення
    def translate_mood_label(key, lang='uk'):
        if not key:
            return 'Немає даних' if lang == 'uk' else 'No data'
        
        mapping = {
            'uk': {
                'happy': 'Щасливий',
                'neutral': 'Нейтральний',
                'sad': 'Сумний',
                'calm': 'Спокійний',
                'energetic': 'Енергійний',
                'anxious': 'Тривожний',
                'angry': 'Злий',
                'tired': 'Втомлений'
            },
            'en': {
                'happy': 'Happy',
                'neutral': 'Neutral',
                'sad': 'Sad',
                'calm': 'Calm',
                'energetic': 'Energetic',
                'anxious': 'Anxious',
                'angry': 'Angry',
                'tired': 'Tired'
            }
        }
        
        lang_mapping = mapping.get(lang, mapping['uk'])
        return lang_mapping.get(key, key)

    most_common_mood = translate_mood_label(raw_most_common, lang)
    
    # Дані для графіків (тільки для поточного користувача)
    entries = MoodEntry.query.filter(
        MoodEntry.user_id == user_id,
        MoodEntry.date >= month_ago
    ).order_by(MoodEntry.date).all()
    
    mood_labels = {
        'uk': ['Щасливий', 'Нейтральний', 'Сумний'],
        'en': ['Happy', 'Neutral', 'Sad']
    }
    moods = mood_labels.get(lang, mood_labels['uk'])
    
    mood_data = {
        'dates': [e.date.strftime('%Y-%m-%d') for e in entries],
        'values': [1 if e.mood == 'happy' else 0.5 if e.mood == 'neutral' else 0 for e in entries],
        'moods': moods,
        'counts': [
            sum(1 for e in entries if e.mood == 'happy'),
            sum(1 for e in entries if e.mood == 'neutral'),
            sum(1 for e in entries if e.mood == 'sad')
        ]
    }
    # Обчислюємо категоріальний середній настрій з числового відображення та перекладаємо
    if mood_data['values']:
        avg_val = sum(mood_data['values']) / len(mood_data['values'])
        # Map average value to nearest category: >0.66 -> happy, >0.33 -> neutral, else sad
        if avg_val > 0.66:
            average_mood = translate_mood_label('happy', lang)
        elif avg_val > 0.33:
            average_mood = translate_mood_label('neutral', lang)
        else:
            average_mood = translate_mood_label('sad', lang)
    else:
        average_mood = '—'

    # Статистика сну
    sleep_entries = MoodEntry.query.filter(
        MoodEntry.user_id == user_id,
        MoodEntry.date >= month_ago,
        MoodEntry.sleep_hours != None
    ).all()
    
    sleep_stats = {
        'total_nights': len(sleep_entries),
        'average_hours': 0,
        'best_night': 0,
        'worst_night': 0,
        'average_quality': 0
    }
    
    if sleep_entries:
        sleep_hours_list = [e.sleep_hours for e in sleep_entries if e.sleep_hours]
        sleep_quality_list = [e.sleep_quality for e in sleep_entries if e.sleep_quality]
        
        if sleep_hours_list:
            sleep_stats['average_hours'] = sum(sleep_hours_list) / len(sleep_hours_list)
            sleep_stats['best_night'] = max(sleep_hours_list)
            sleep_stats['worst_night'] = min(sleep_hours_list)
        
        if sleep_quality_list:
            quality_avg = sum(sleep_quality_list) / len(sleep_quality_list)
            sleep_stats['average_quality'] = round(quality_avg, 1)

    # Quote-related stats are client-side in many deployments; provide safe defaults
    quotes_count = 0
    favorite_quotes_count = 0
    daily_quote = ''
    daily_quote_author = ''
    
    return render_template('statistics.html',
                         monthly_entries=monthly_entries,
                         most_common_mood=most_common_mood,
                         average_mood=average_mood,
                         mood_data=mood_data,
                         sleep_stats=sleep_stats,
                         quotes_count=quotes_count,
                         favorite_quotes_count=favorite_quotes_count,
                         daily_quote=daily_quote,
                         daily_quote_author=daily_quote_author)

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Головна панель адміністратора з посиланнями на ключові розділи."""
    return render_template('admin_dashboard.html')


@app.route('/admin/feedback')
@admin_required
def admin_feedback():
    """Адмін-панель для перегляду та видалення відгуків."""
    return render_template('admin_feedback.html')

@app.route('/admin/products')
@admin_required
def admin_products():
    """Адмін-панель для управління продуктами."""
    return render_template('admin_products.html')

@app.route('/admin/orders')
@admin_required
def admin_orders():
    """Адмін-панель для управління замовленнями."""
    return render_template('admin_orders.html')


@app.route('/admin/users')
@admin_required
def admin_users():
    """Адмін-панель для керування ролями користувачів."""
    return render_template('admin_users.html')


# -------------------- API Авторизації --------------------
@app.route('/auth/register', methods=['GET', 'POST'])
def register():
    """Сторінка реєстрації та обробка реєстрації нового користувача."""
    if request.method == 'GET':
        return render_template('register.html')
    
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        password = (data.get('password') or '').strip()
        
        if not email or not password:
            return jsonify({'status': 'error', 'message': 'Email та пароль обов\'язкові'}), 400
        
        if len(password) < 6:
            return jsonify({'status': 'error', 'message': 'Пароль має бути мінімум 6 символів'}), 400
        
        # Перевірка чи email вже існує
        if User.query.filter_by(email=email).first():
            return jsonify({'status': 'error', 'message': 'Користувач з таким email вже існує'}), 400
        
        # Перший зареєстрований користувач стає адміном автоматично
        is_first_admin = User.query.filter_by(is_admin=True).first() is None

        # Створення користувача
        user = User(email=email)
        if is_first_admin:
            user.is_admin = True
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Автоматичний вхід після реєстрації
        session['user_id'] = user.id
        if is_first_admin:
            logging.info("Перший користувач %s отримав права адміністратора", email)
        
        return jsonify({'status': 'success', 'message': 'Реєстрація успішна', 'user': user.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Register error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    """Сторінка логіну та обробка входу користувача."""
    if request.method == 'GET':
        return render_template('login.html')
    
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        password = (data.get('password') or '').strip()
        
        if not email or not password:
            logging.warning('Login failed: empty credentials')
            return jsonify({'status': 'error', 'message': 'Email та пароль обов\'язкові'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            logging.warning('Login failed: user not found %s', email)
            return jsonify({'status': 'error', 'message': 'Невірний email або пароль'}), 401
        
        if not user.check_password(password):
            logging.warning('Login failed: wrong password %s', email)
            return jsonify({'status': 'error', 'message': 'Невірний email або пароль'}), 401
        
        ensure_admin_presence(user)
        try:
            db.session.refresh(user)
        except Exception:
            logging.debug('Не вдалося оновити кеш користувача після входу, буде використана поточна модель')
        
        session['user_id'] = user.id
        session.permanent = True
        logging.info('Login success for %s (session set: %s)', email, session.get('user_id'))
        
        return jsonify({'status': 'success', 'message': 'Вхід успішний', 'user': user.to_dict()}), 200
        
    except Exception as e:
        logging.error(f"Login error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/auth/logout', methods=['GET', 'POST'])
def logout():
    """Вихід користувача."""
    session.clear()  # Повністю очищаємо сесію
    if request.method == 'GET':
        # Якщо GET запит (клік на посилання) - редірект на головну
        return redirect(url_for('index'))
    else:
        # Якщо POST (AJAX) - повертаємо JSON
        return jsonify({'status': 'success', 'message': 'Вихід успішний'}), 200


@app.route('/api/me', methods=['GET'])
def get_current_user():
    """Отримати дані поточного користувача."""
    logging.debug(f"GET /api/me - session keys: {list(session.keys())}, user_id: {session.get('user_id')}")
    logging.debug(f"GET /api/me - request cookies: {request.cookies}")
    
    if 'user_id' not in session:
        logging.warning(f"GET /api/me - no user_id in session. Session: {dict(session)}")
        return jsonify({'status': 'error', 'message': 'Не авторизовано'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        logging.warning(f"GET /api/me - user {session['user_id']} not found in DB")
        session.pop('user_id', None)
        return jsonify({'status': 'error', 'message': 'Користувач не знайдений'}), 404
    
    logging.info(f"GET /api/me - user found: {user.email}")
    return jsonify({'status': 'success', 'user': user.to_dict()}), 200


@app.route('/api/session-debug', methods=['GET'])
def session_debug():
    """Debug: перевіримо, яка сесія на сервері."""
    return jsonify({
        'session_keys': list(session.keys()),
        'user_id': session.get('user_id'),
        'cookies': dict(request.cookies),
        'all_session': dict(session)
    }), 200


@app.route('/api/avatars', methods=['GET'])
def list_avatars():
    """Повертає список доступних аватарів з урахуванням premium-статусу."""
    if 'user_id' not in session:
        return jsonify({
            'status': 'success',
            'avatars': AVAILABLE_AVATARS,
            'premium_avatars': [],
            'premium_locked': PREMIUM_AVATARS
        }), 200
    
    user = User.query.get(session['user_id'])
    if user and user.is_premium:
        return jsonify({
            'status': 'success',
            'avatars': AVAILABLE_AVATARS,
            'premium_avatars': PREMIUM_AVATARS,
            'premium_locked': []
        }), 200
    else:
        return jsonify({
            'status': 'success',
            'avatars': AVAILABLE_AVATARS,
            'premium_avatars': [],
            'premium_locked': PREMIUM_AVATARS
        }), 200


@app.route('/api/me/avatar', methods=['PUT'])
@login_required
def update_avatar():
    """Оновлює аватар поточного користувача."""
    try:
        data = request.get_json(silent=True) or {}
        avatar_key = (data.get('avatar') or '').strip()

        user = User.query.get(session['user_id'])
        if not user:
            session.pop('user_id', None)
            return jsonify({'status': 'error', 'message': 'Користувача не знайдено'}), 404

        # Перевіряємо, чи аватар доступний для користувача
        all_allowed = AVAILABLE_AVATARS[:]
        if user.is_premium:
            all_allowed.extend(PREMIUM_AVATARS)
        
        if avatar_key and avatar_key not in all_allowed:
            return jsonify({'status': 'error', 'message': 'Аватар недоступний'}), 403

        user.avatar = avatar_key or None
        db.session.commit()

        return jsonify({'status': 'success', 'user': user.to_dict()}), 200
    except Exception as exc:
        db.session.rollback()
        logging.error('Не вдалося оновити аватар: %s', exc)
        return jsonify({'status': 'error', 'message': 'Не вдалося оновити аватар'}), 500


@app.route('/api/journal', methods=['GET'])
@login_required
def list_entries():
    """Return a list of journal entries as JSON.

    Supports optional query params:
    - month: YYYY-MM to filter a specific month
    - mood: filter by mood value (happy, neutral, sad)

    Returns a JSON list of entry dicts using the model's to_dict() helper.
    """
    try:
        user_id = session['user_id']
        month = request.args.get('month')
        mood = request.args.get('mood')
        
        # Фільтруємо тільки записи поточного користувача
        query = MoodEntry.query.filter_by(user_id=user_id)
        
        if month:
            year, month = map(int, month.split('-'))
            query = query.filter(
                extract('year', MoodEntry.date) == year,
                extract('month', MoodEntry.date) == month
            )
            
        if mood:
            query = query.filter(MoodEntry.mood == mood)
            
        entries = query.order_by(MoodEntry.date.desc()).all()
        
        return jsonify([e.to_dict() for e in entries]), 200
        
    except Exception as e:
        logging.error(f"Error listing entries: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Помилка при отриманні записів: {str(e)}'
        }), 500

@app.route('/api/journal', methods=['POST'])
@login_required
@swag_from('docs/swagger/journal_post.yml')
def add_entry():
    """Add a journal entry with validation."""
    try:
        user_id = session['user_id']
        
        # Debug: логування вхідних даних
        logging.info(f"Received journal data: {request.get_json()}")
        
        # Валідація вхідних даних
        validated_data, error = validate_request_data(create_journal_entry_schema)
        if error:
            logging.error(f"Validation error: {error}")
            return error
        
        # Обробка activities: конвертуємо список в comma-separated string
        activities_input = validated_data.get('activities', [])
        if isinstance(activities_input, list) and activities_input:
            activities = ','.join(activities_input)
        elif isinstance(activities_input, str) and activities_input:
            activities = activities_input
        else:
            activities = None
        
        # Обробка даних про сон
        sleep_quality = validated_data.get('sleep_quality')
        sleep_hours = validated_data.get('sleep_hours')
        
        # Валідація sleep_quality (1-4)
        if sleep_quality is not None:
            try:
                sleep_quality = int(sleep_quality)
                if not (1 <= sleep_quality <= 4):
                    sleep_quality = None
            except (ValueError, TypeError):
                sleep_quality = None
        
        # Валідація sleep_hours (0-12)
        if sleep_hours is not None:
            try:
                sleep_hours = float(sleep_hours)
                if not (0 <= sleep_hours <= 12):
                    sleep_hours = None
            except (ValueError, TypeError):
                sleep_hours = None
        
        entry = MoodEntry(
            mood=validated_data['mood'],
            date=validated_data['date'],
            title=validated_data['title'],
            user_id=user_id,
            content=validated_data.get('content'),
            activities=activities,
            sleep_quality=sleep_quality,
            sleep_hours=sleep_hours
        )
        
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Запис успішно збережено',
            'data': entry.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding entry: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Внутрішня помилка сервера'
        }), 500

@app.route('/api/journal/<int:entry_id>', methods=['PUT'])
@login_required
def update_entry(entry_id):
    """Оновлює існуючий запис щоденника."""
    try:
        user_id = session['user_id']
        entry = MoodEntry.query.get_or_404(entry_id)
        
        # Перевіряємо що запис належить користувачу
        if entry.user_id != user_id:
            return jsonify({
                'status': 'error',
                'message': 'Доступ заборонено'
            }), 403
        
        data = request.get_json() if request.is_json else request.form
        
        # Оновлюємо настрій якщо він наданий і валідний
        if 'mood' in data:
            if data['mood'] not in MoodEntry.VALID_MOODS:
                return jsonify({
                    'status': 'error',
                    'message': f'Недійсне значення настрою. Допустимі значення: {", ".join(MoodEntry.VALID_MOODS)}'
                }), 400
            entry.mood = data['mood']
            
        # Оновлюємо інші поля якщо вони надані
        if 'title' in data:
            entry.title = data['title'].strip()
            
        if 'content' in data:
            entry.content = data['content'].strip()
            
        if 'activities' in data:
            entry.activities = ','.join(data['activities']) if data['activities'] else None
            
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Запис успішно оновлено',
            'data': entry.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Помилка при оновленні: {str(e)}'
        }), 500

@app.route('/api/journal/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_entry(entry_id):
    """Delete a journal entry."""
    try:
        user_id = session['user_id']
        entry = MoodEntry.query.get_or_404(entry_id)
        
        # Перевіряємо що запис належить користувачу
        if entry.user_id != user_id:
            return jsonify({
                'status': 'error',
                'message': 'Доступ заборонено'
            }), 403
        
        db.session.delete(entry)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Запис успішно видалено'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Помилка при видаленні: {str(e)}'
        }), 500


# -------------------- Експорт та Аналітика (MVP) --------------------
@app.route('/api/journal/export', methods=['GET'])
@login_required
def export_journal():
    """Експорт записів щоденника у CSV або JSON.

    Параметр запиту:
    - format: 'csv' (за замовчуванням) або 'json'
    """
    try:
        user_id = session['user_id']
        out_format = (request.args.get('format') or 'csv').strip().lower()
        entries = MoodEntry.query.filter_by(user_id=user_id).order_by(MoodEntry.date.asc(), MoodEntry.id.asc()).all()

        if out_format == 'json':
            return jsonify({
                'status': 'success',
                'count': len(entries),
                'data': [e.to_dict() for e in entries]
            }), 200

        # Підготовка CSV
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['id','date','mood','title','activities','content'])
        for e in entries:
            writer.writerow([
                e.id,
                e.date.isoformat(),
                e.mood,
                e.title or '',
                (e.activities or ''),
                (e.content or '').replace('\n', ' ').strip()
            ])
        csv_data = buf.getvalue()
        resp = app.response_class(
            csv_data,
            mimetype='text/csv; charset=utf-8'
        )
        resp.headers['Content-Disposition'] = 'attachment; filename="journal_export.csv"'
        return resp
    except Exception as exc:
        logging.exception('Помилка експорту журналу')
        return jsonify({'status':'error','message':str(exc)}), 500


@app.route('/api/stats/trends', methods=['GET'])
@login_required
def stats_trends():
    """Зведена аналітика: теплокарта та середні значення.

    Повертає:
    - heatmap: список {date, value, mood} за останні 365 днів
    - summary_30d: підсумок за 30 днів (лічильники настроїв, середній настрій)
    """
    try:
        user_id = session['user_id']
        today = datetime.utcnow().date()
        year_ago = today - timedelta(days=364)
        q = MoodEntry.query.filter(
            MoodEntry.user_id == user_id,
            MoodEntry.date >= year_ago
        ).order_by(MoodEntry.date.asc()).all()

        mood_to_numeric = {'happy': 1.0, 'neutral': 0.5, 'sad': 0.0}

        heatmap = [{'date': e.date.isoformat(),
                    'value': mood_to_numeric.get(e.mood, 0.5),
                    'mood': e.mood} for e in q]

        # Останні 30 днів
        month_ago = today - timedelta(days=29)
        last_30 = [e for e in q if e.date >= month_ago]
        counts = {
            'happy': sum(1 for e in last_30 if e.mood == 'happy'),
            'neutral': sum(1 for e in last_30 if e.mood == 'neutral'),
            'sad': sum(1 for e in last_30 if e.mood == 'sad'),
        }
        values = [mood_to_numeric.get(e.mood, 0.5) for e in last_30]
        avg_val = (sum(values)/len(values)) if values else None

        def translate_avg(v):
            if v is None:
                return 'Невідомо'
            if v > 0.66:
                return 'Щасливий'
            if v > 0.33:
                return 'Нейтральний'
            return 'Сумний'

        return jsonify({
            'status': 'success',
            'heatmap': heatmap,
            'summary_30d': {
                'counts': counts,
                'average_value': avg_val,
                'average_label': translate_avg(avg_val),
                'days': len(last_30)
            }
        }), 200
    except Exception as exc:
        logging.exception('Помилка розрахунку трендів')
        return jsonify({'status':'error','message':str(exc)}), 500


# -------------------- API Звичок & Цілей --------------------
@app.route('/api/habits', methods=['GET'])
@login_required
def get_habits():
    try:
        user_id = session['user_id']
        # Оптимізація: отримуємо тільки активні habits користувача
        habits = Habit.query.filter_by(user_id=user_id).order_by(Habit.id).all()
        today = datetime.utcnow().date()
        month_ago = today - timedelta(days=29)

        result = []
        for h in habits:
            # include completions in the last 30 days
            comps = [c.date.isoformat() for c in h.completions if c.date >= month_ago]
            result.append({
                'id': h.id,
                'name': h.name,
                'type': h.type,
                'created_at': h.created_at.isoformat(),
                'completions': comps,
                'completed': today.isoformat() in comps
            })

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error fetching habits: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/habits', methods=['POST'])
@login_required
def create_habit():
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        habit_type = (data.get('type') or 'daily').strip()
        
        if not name:
            return jsonify({'status': 'error', 'message': 'Назва звички обов\'язкова'}), 400
        
        # Прив'язати звичку до поточного користувача
        user_id = session.get('user_id')
        habit = Habit(name=name, type=habit_type, user_id=user_id)
        db.session.add(habit)
        db.session.commit()
        
        return jsonify({'status': 'success', 'data': habit.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating habit: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting habit: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/habits/<int:habit_id>/toggle', methods=['POST'])
def toggle_habit(habit_id):
    try:
        habit = Habit.query.get_or_404(habit_id)
        today = datetime.utcnow().date()
        comp = HabitCompletion.query.filter_by(habit_id=habit.id, date=today).first()
        if comp:
            db.session.delete(comp)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Unchecked', 'completed': False}), 200
        else:
            newc = HabitCompletion(habit_id=habit.id, date=today)
            db.session.add(newc)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Checked', 'completed': True}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error toggling habit: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/habits/<int:habit_id>', methods=['DELETE'])
def delete_habit(habit_id):
    try:
        habit = Habit.query.get_or_404(habit_id)
        db.session.delete(habit)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Habit deleted'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting habit: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/goals', methods=['GET'])
def get_goals():
    try:
        # Повертаємо тільки цілі поточного користувача
        user_id = session.get('user_id')
        if user_id:
            goals = MonthlyGoal.query.filter_by(user_id=user_id).order_by(MonthlyGoal.deadline).all()
        else:
            goals = []
        return jsonify([g.to_dict() for g in goals]), 200
    except Exception as e:
        logging.error(f"Error fetching goals: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/goals', methods=['POST'])
def create_goal():
    try:
        data = request.get_json(silent=True)
        if not data or 'name' not in data or 'deadline' not in data:
            return jsonify({'status': 'error', 'message': 'Missing name or deadline'}), 400
        from datetime import datetime as _dt
        deadline = _dt.strptime(data['deadline'], '%Y-%m-%d').date()
        # Прив'язати ціль до користувача
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'status': 'error', 'message': 'Не авторизовано'}), 401
        goal = MonthlyGoal(name=data['name'].strip(), deadline=deadline, user_id=user_id)
        db.session.add(goal)
        db.session.commit()
        return jsonify({'status': 'success', 'data': goal.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating goal: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    try:
        goal = MonthlyGoal.query.get_or_404(goal_id)
        db.session.delete(goal)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Goal deleted'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting goal: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/goals/<int:goal_id>/toggle', methods=['POST'])
def toggle_goal(goal_id):
    try:
        goal = MonthlyGoal.query.get_or_404(goal_id)
        goal.completed = not bool(goal.completed)
        db.session.commit()
        return jsonify({'status': 'success', 'data': goal.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error toggling goal: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# -------------------- Feedback API --------------------
@app.route('/api/feedback', methods=['POST'])
@swag_from('docs/swagger/feedback_post.yml')
def create_feedback():
    """Create a feedback entry with validation."""
    try:
        # Валідація вхідних даних
        validated_data, error = validate_request_data(create_feedback_schema)
        if error:
            return error
        
        fb = Feedback(
            name=validated_data['name'],
            email=validated_data['email'],
            message=validated_data['message'],
            rating=validated_data.get('rating')
        )
        db.session.add(fb)
        db.session.commit()
        
        return jsonify({'status': 'success', 'data': fb.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating feedback: {e}")
        return jsonify({'status': 'error', 'message': 'Внутрішня помилка сервера'}), 500

@app.route('/api/feedback', methods=['GET'])
@swag_from('docs/swagger/feedback_get.yml')
def list_feedback():
    """List recent feedback entries (latest 50)."""
    try:
        q = Feedback.query.order_by(Feedback.created_at.desc()).limit(50).all()
        return jsonify([f.to_dict() for f in q]), 200
    except Exception as e:
        logging.error(f"Error listing feedback: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/feedback/<int:feedback_id>', methods=['DELETE'])
@admin_required
def delete_feedback(feedback_id):
    """Видалити відгук за ID (тільки адмін)."""
    try:
        fb = Feedback.query.get_or_404(feedback_id)
        db.session.delete(fb)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Відгук видалено', 'id': feedback_id}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting feedback: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# -------------------- API Продуктів --------------------
@app.route('/api/products', methods=['GET'])
@swag_from('docs/swagger/products_get.yml')
def get_products():
    """Отримати список продуктів (тільки активні)."""
    try:
        # Всі користувачі (адмін і звичайні) бачать тільки активні продукти
        products = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).all()
        
        return jsonify([p.to_dict() for p in products]), 200
    except Exception as e:
        logging.error(f"Error listing products: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/products', methods=['POST'])
@admin_required
def create_product():
    """Створити новий продукт (тільки адмін)."""
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        slug = (data.get('slug') or '').strip()
        product_type = (data.get('type') or '').strip()
        description = (data.get('description') or '').strip()
        price = data.get('price', 0.0)
        
        if not name or not slug or not product_type:
            return jsonify({'status': 'error', 'message': 'Name, slug та type обов\'язкові'}), 400
        
        # Перевірка унікальності slug
        if Product.query.filter_by(slug=slug).first():
            return jsonify({'status': 'error', 'message': 'Продукт з таким slug вже існує'}), 400
        
        product = Product(
            name=name,
            slug=slug,
            type=product_type,
            description=description,
            price=float(price),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Продукт створено', 'product': product.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating product: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/products/<int:product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    """Оновити продукт (тільки адмін)."""
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json(silent=True) or {}
        
        if 'name' in data:
            product.name = data['name'].strip()
        if 'slug' in data:
            new_slug = data['slug'].strip()
            # Перевірка унікальності нового slug
            existing = Product.query.filter_by(slug=new_slug).first()
            if existing and existing.id != product_id:
                return jsonify({'status': 'error', 'message': 'Продукт з таким slug вже існує'}), 400
            product.slug = new_slug
        if 'type' in data:
            product.type = data['type'].strip()
        if 'description' in data:
            product.description = data['description'].strip()
        if 'price' in data:
            product.price = float(data['price'])
        if 'is_active' in data:
            product.is_active = bool(data['is_active'])
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Продукт оновлено', 'product': product.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating product: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@admin_required
def delete_product(product_id):
    """Видалити продукт з магазину (тільки адмін). Soft delete - деактивуємо."""
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'status': 'error', 'message': 'Продукт не знайдено'}), 404
        
        # Soft delete - позначаємо як неактивний (保留в БД для історії замовлень)
        product.is_active = False
        db.session.commit()
        
        logging.info(f"Product {product_id} deactivated by user {session.get('user_id')}")
        return jsonify({'status': 'success', 'message': 'Продукт видалено з магазину', 'id': product_id}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting product {product_id}: {e}")
        return jsonify({'status': 'error', 'message': f'Помилка видалення: {str(e)}'}), 500


# -------------------- API Замовлень --------------------
@app.route('/api/orders', methods=['POST'])
@login_required
@swag_from('docs/swagger/orders_post.yml')
def create_order():
    """Створити нове замовлення (потрібен вхід)."""
    try:
        # Валідація вхідних даних
        validated_data, error = validate_request_data(create_order_schema)
        if error:
            return error
        
        items_data = validated_data['items']
        user_id = session['user_id']
        
        # Створюємо замовлення
        order = Order(user_id=user_id, status='new')
        db.session.add(order)
        db.session.flush()  # Щоб отримати order.id для items
        
        # Додаємо елементи замовлення
        for item_data in items_data:
            product_id = item_data['product_id']
            quantity = item_data['quantity']
            
            product = Product.query.get(product_id)
            if not product or not product.is_active:
                db.session.rollback()
                return jsonify({
                    'status': 'error',
                    'message': f'Продукт #{product_id} недоступний'
                }), 404
            
            subtotal = product.price * quantity
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
                subtotal=subtotal
            )
            db.session.add(order_item)
        
        # Розраховуємо загальну суму
        order.calculate_total()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Замовлення створено',
            'order': order.to_dict(include_items=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating order: {e}")
        return jsonify({'status': 'error', 'message': 'Внутрішня помилка сервера'}), 500


@app.route('/api/orders', methods=['GET'])
@login_required
def get_orders():
    """Отримати список замовлень (користувач - свої; адмін - всі)."""
    try:
        user = User.query.get(session['user_id'])
        
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)  # max 100 orders per page
        
        if user.is_admin:
            paginated = Order.query.order_by(Order.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
        else:
            paginated = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
        
        return jsonify({
            'orders': [o.to_dict(include_items=False) for o in paginated.items],
            'page': page,
            'total': paginated.total,
            'pages': paginated.pages
        }), 200
    except Exception as e:
        logging.error(f"Error listing orders: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/orders/<int:order_id>', methods=['GET'])
@login_required
def get_order(order_id):
    """Отримати деталі замовлення."""
    try:
        user = User.query.get(session['user_id'])
        order = Order.query.get_or_404(order_id)
        
        # Перевірка доступу: власник або адмін
        if order.user_id != user.id and not user.is_admin:
            return jsonify({'status': 'error', 'message': 'Доступ заборонено'}), 403
        
        return jsonify({'status': 'success', 'order': order.to_dict(include_items=True)}), 200
    except Exception as e:
        logging.error(f"Error getting order: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@admin_required
def update_order_status(order_id):
    """Оновити статус замовлення (тільки адмін)."""
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json(silent=True) or {}
        new_status = (data.get('status') or '').strip()
        
        allowed_statuses = ['new', 'processing', 'completed', 'canceled']
        if new_status not in allowed_statuses:
            return jsonify({'status': 'error', 'message': f'Невірний статус. Дозволені: {", ".join(allowed_statuses)}'}), 400
        
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Статус оновлено', 'order': order.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating order status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
@admin_required
def delete_order(order_id):
    """Видалити замовлення (тільки адмін)."""
    try:
        order = Order.query.get_or_404(order_id)
        db.session.delete(order)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Замовлення видалено', 'id': order_id}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting order: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# -------------------- API Оплати --------------------
@app.route('/api/payments/methods', methods=['GET'])
@swag_from('docs/swagger/payments_methods_get.yml')
def get_payment_methods():
    """Отримати доступні методи оплати."""
    methods = [
        {
            'id': 'card',
            'name': 'Банківська картка',
            'icon': '💳',
            'description': 'Visa, Mastercard, American Express'
        },
        {
            'id': 'online_banking',
            'name': 'Інтернет-банкінг',
            'icon': '🏦',
            'description': 'Оплата через онлайн-банкінг'
        },
        {
            'id': 'paypal',
            'name': 'PayPal',
            'icon': '🅿️',
            'description': 'Швидка оплата через PayPal'
        }
    ]
    return jsonify({'status': 'success', 'methods': methods}), 200


@app.route('/api/payments', methods=['POST'])
@login_required
@swag_from('docs/swagger/payments_post.yml')
def create_payment():
    """Створити платіж для замовлення."""
    try:
        # Валідація вхідних даних
        validated_data, error = validate_request_data(create_payment_schema)
        if error:
            return error
        
        order_id = validated_data['order_id']
        payment_method = validated_data['payment_method']
        
        # Додаткова валідація для картки
        if payment_method == 'card':
            required_card_fields = ['card_number', 'card_holder', 'card_expiry', 'card_cvv']
            missing_fields = [f for f in required_card_fields if f not in validated_data or not validated_data[f]]
            if missing_fields:
                return jsonify({
                    'status': 'error',
                    'message': f'Для оплати карткою обов\'язкові поля: {", ".join(missing_fields)}'
                }), 400
        
        # Перевірка замовлення
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'status': 'error', 'message': 'Замовлення не знайдено'}), 404
        
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # Перевірка чи вже є оплата (для ідемпотентності повертаємо існуючий)
        existing_payment = Payment.query.filter_by(order_id=order.id).first()
        if existing_payment:
            return jsonify({
                'status': 'success',
                'message': 'Платіж вже існує для цього замовлення',
                'payment': existing_payment.to_dict(),
                'order': order.to_dict()
            }), 200
        
        # Створення платежу
        payment = Payment(
            order_id=order.id,
            payment_method=payment_method,
            amount=order.total_amount,
            status='pending'
        )
        
        # Обробка деталей карти
        if payment_method == 'card':
            card_number = validated_data['card_number'].replace(' ', '').strip()
            if len(card_number) >= 4:
                payment.card_last4 = card_number[-4:]
            payment.card_brand = validated_data.get('card_brand', 'Unknown')
        
        # Симуляція обробки платежу
        import uuid
        prefix = {'card': 'TXN', 'online_banking': 'BANK', 'paypal': 'PP'}.get(payment_method, 'TXN')
        payment.transaction_id = f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
        payment.status = 'completed'
        payment.completed_at = datetime.utcnow()
        
        # Для цифрових продуктів (Premium) - одразу completed
        is_digital = any('premium' in (item.product.name or '').lower() or 
                       'преміум' in (item.product.name or '').lower() 
                       for item in order.items)
        order.status = 'completed' if is_digital else 'processing'
        
        # Активація Premium для користувача
        if is_digital and user:
            user.is_premium = True
            logging.info(f"Premium активовано для користувача {user.email}")
        
        db.session.add(payment)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Платіж створено успішно',
            'payment': payment.to_dict(),
            'order': order.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"Error creating payment: {e}\n{error_details}")
        return jsonify({
            'status': 'error', 
            'message': 'Внутрішня помилка сервера',
            'error': str(e) if app.debug else None
        }), 500


@app.route('/api/payments/<int:payment_id>', methods=['GET'])
@login_required
def get_payment(payment_id):
    """Отримати деталі платежу."""
    try:
        payment = Payment.query.get_or_404(payment_id)
        user = User.query.get(session['user_id'])
        
        # Перевірка доступу
        if payment.order.user_id != user.id and not user.is_admin:
            return jsonify({'status': 'error', 'message': 'Доступ заборонено'}), 403
        
        return jsonify({
            'status': 'success',
            'payment': payment.to_dict(),
            'order': payment.order.to_dict(include_items=True)
        }), 200
    except Exception as e:
        logging.error(f"Error getting payment: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/payments/<int:payment_id>/status', methods=['PUT'])
@admin_required
def update_payment_status(payment_id):
    """Оновити статус платежу (тільки адмін)."""
    try:
        payment = Payment.query.get_or_404(payment_id)
        data = request.get_json(silent=True) or {}
        new_status = data.get('status', '').strip()
        
        allowed_statuses = ['pending', 'completed', 'failed', 'refunded']
        if new_status not in allowed_statuses:
            return jsonify({'status': 'error', 'message': f'Невірний статус. Дозволені: {", ".join(allowed_statuses)}'}), 400
        
        payment.status = new_status
        
        if new_status == 'completed' and not payment.completed_at:
            payment.completed_at = datetime.utcnow()
            payment.order.status = 'processing'
        elif new_status == 'failed':
            payment.order.status = 'canceled'
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Статус платежу оновлено',
            'payment': payment.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating payment status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# -------------------- API Адміністрування Користувачів --------------------
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_list_users():
    """Повернути список усіх користувачів з їх ролями."""
    try:
        # Пагінація для списку користувачів (max 50 на сторінку)
        page = request.args.get('page', 1, type=int)
        limit = min(int(request.args.get('limit', 50, type=int)), 50)
        paginated = User.query.order_by(User.created_at.asc()).paginate(page=page, per_page=limit, error_out=False)
        users = paginated.items
        return jsonify({
            'status': 'success',
            'users': [u.to_dict() for u in users],
            'page': page,
            'total': paginated.total,
            'pages': paginated.pages
        }), 200
    except Exception as e:
        logging.error(f"Error listing users: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/admin/users/<int:user_id>/admin', methods=['PUT'])
@admin_required
def admin_set_role(user_id):
    """Змінити статус адміністратора для користувача."""
    try:
        data = request.get_json(silent=True) or {}
        if 'is_admin' not in data:
            return jsonify({'status': 'error', 'message': 'Вкажіть поле is_admin'}), 400

        target_user = User.query.get_or_404(user_id)
        primary_email = 'admin_1@gmail.com'

        desired_state = data['is_admin']
        if isinstance(desired_state, str):
            desired_state = desired_state.strip().lower() in ('1', 'true', 'yes', 'on')
        else:
            desired_state = bool(desired_state)

        if target_user.email == primary_email and not desired_state:
            return jsonify({'status': 'error', 'message': 'Неможливо забрати права у головного адміністратора'}), 400

        if not desired_state:
            admin_count = User.query.filter_by(is_admin=True).count()
            if target_user.is_admin and admin_count <= 1:
                return jsonify({'status': 'error', 'message': 'Повинен залишитися хоча б один адміністратор'}), 400

        target_user.is_admin = desired_state
        db.session.commit()

        return jsonify({'status': 'success', 'user': target_user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating admin role: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/admin/users/<int:user_id>/premium', methods=['PUT'])
@admin_required
def admin_set_premium(user_id):
    """Увімкнути/вимкнути преміум-статус для користувача."""
    try:
        data = request.get_json(silent=True) or {}
        if 'is_premium' not in data:
            return jsonify({'status': 'error', 'message': 'Вкажіть поле is_premium'}), 400

        target_user = User.query.get_or_404(user_id)

        desired_state = data['is_premium']
        if isinstance(desired_state, str):
            desired_state = desired_state.strip().lower() in ('1', 'true', 'yes', 'on')
        else:
            desired_state = bool(desired_state)

        target_user.is_premium = desired_state
        now = datetime.utcnow()
        if desired_state and not target_user.premium_started_at:
            target_user.premium_started_at = now
        if not desired_state:
            # опційно можна обнуляти дату завершення
            target_user.premium_expires_at = None

        db.session.commit()

        return jsonify({'status': 'success', 'user': target_user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating premium status: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """Видалити користувача (не можна видаляти головного адміністратора або останнього адміна)."""
    try:
        user = User.query.get_or_404(user_id)
        primary_email = 'admin_1@gmail.com'

        if user.email == primary_email:
            return jsonify({'status': 'error', 'message': 'Неможливо видалити головного адміністратора'}), 400

        if user.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': 'Повинен залишитися хоча б один адміністратор'}), 400

        db.session.delete(user)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Користувача видалено', 'id': user_id}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting user: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/admin/users/<int:user_id>/reset-advice-lock', methods=['POST'])
@admin_required
def admin_reset_advice_lock(user_id):
    """Дозволити користувачу отримати ще одну пораду сьогодні (один раз)."""
    try:
        user = User.query.get_or_404(user_id)
        user.advice_unlock_once = True
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'Блокіровку скинуто для {user.email}'}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error resetting advice lock: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# -------------------- Premium Features API --------------------

@app.route('/api/premium/mood-predictor', methods=['GET'])
@login_required
def mood_predictor():
    """Передбачає настрій на завтра на основі історії (Premium feature)."""
    try:
        user = User.query.get(session['user_id'])
        if not user or not user.is_premium:
            return jsonify({
                'status': 'error',
                'message': 'Ця функція доступна тільки для Premium користувачів',
                'premium_required': True
            }), 403

        # Отримуємо останні 30 днів записів ПОТОЧНОГО користувача
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        recent_entries = MoodEntry.query.filter(
            MoodEntry.user_id == user.id,
            MoodEntry.date >= thirty_days_ago
        ).order_by(MoodEntry.date.desc()).limit(30).all()

        if len(recent_entries) < 3:
            return jsonify({
                'status': 'info',
                'prediction': 'neutral',
                'confidence': 0,
                'message': 'Недостатньо даних для прогнозу. Додай більше записів!',
                'insights': []
            }), 200

        # Проста ML логіка: аналізуємо паттерни
        mood_counts = {'happy': 0, 'neutral': 0, 'sad': 0}
        for entry in recent_entries:
            mood_counts[entry.mood] += 1

        total = len(recent_entries)
        mood_percentages = {k: (v/total)*100 for k, v in mood_counts.items()}
        
        # Тренд останніх 7 днів vs попередніх 7
        last_week = recent_entries[:7]
        prev_week = recent_entries[7:14] if len(recent_entries) >= 14 else []
        
        def avg_mood_score(entries):
            scores = {'happy': 3, 'neutral': 2, 'sad': 1}
            if not entries: return 2
            return sum(scores[e.mood] for e in entries) / len(entries)
        
        recent_score = avg_mood_score(last_week)
        prev_score = avg_mood_score(prev_week) if prev_week else recent_score
        trend = "up" if recent_score > prev_score else "down" if recent_score < prev_score else "stable"

        # День тижня паттерн
        tomorrow = datetime.utcnow().date() + timedelta(days=1)
        tomorrow_weekday = tomorrow.weekday()  # 0=Mon, 6=Sun
        
        weekday_moods = {}
        for entry in recent_entries:
            wd = entry.date.weekday()
            if wd not in weekday_moods:
                weekday_moods[wd] = []
            weekday_moods[wd].append(entry.mood)
        
        # Prediction logic
        predicted_mood = 'neutral'
        confidence = 50
        
        if tomorrow_weekday in weekday_moods and len(weekday_moods[tomorrow_weekday]) >= 2:
            # Використовуємо історію цього дня тижня
            day_moods = weekday_moods[tomorrow_weekday]
            day_counts = {'happy': day_moods.count('happy'), 
                         'neutral': day_moods.count('neutral'), 
                         'sad': day_moods.count('sad')}
            predicted_mood = max(day_counts, key=day_counts.get)
            confidence = (day_counts[predicted_mood] / len(day_moods)) * 100
        else:
            # Використовуємо загальний тренд
            predicted_mood = max(mood_counts, key=mood_counts.get)
            confidence = mood_percentages[predicted_mood]

        # Корекція на тренд
        if trend == "up" and predicted_mood != 'happy':
            predicted_mood = 'happy' if predicted_mood == 'neutral' else 'neutral'
            confidence = min(confidence + 10, 90)
        elif trend == "down" and predicted_mood != 'sad':
            predicted_mood = 'sad' if predicted_mood == 'neutral' else 'neutral'
            confidence = min(confidence + 10, 90)

        # Генеруємо інсайти
        insights = []
        weekday_names_uk = ['понеділок', 'вівторок', 'середу', 'четвер', 'п\'ятницю', 'суботу', 'неділю']
        tomorrow_name = weekday_names_uk[tomorrow_weekday]
        
        if trend == "up":
            insights.append(f"📈 Твій настрій покращується останнім часом!")
        elif trend == "down":
            insights.append(f"📉 Останнім часом настрій трішки знижується. Подбай про себе!")
        
        if mood_percentages['happy'] > 60:
            insights.append(f"✨ Ти щасливий/а {mood_percentages['happy']:.0f}% часу — це чудово!")
        elif mood_percentages['sad'] > 40:
            insights.append(f"💙 Схоже на складний період. Пам'ятай, що це минає.")
        
        if tomorrow_weekday in weekday_moods:
            insights.append(f"📅 Зазвичай у {tomorrow_name} твій настрій {predicted_mood}")

        return jsonify({
            'status': 'success',
            'prediction': predicted_mood,
            'confidence': round(confidence, 1),
            'trend': trend,
            'tomorrow_date': tomorrow.isoformat(),
            'insights': insights,
            'stats': {
                'total_entries': total,
                'mood_distribution': mood_percentages,
                'recent_trend': trend
            }
        }), 200

    except Exception as e:
        logging.error(f"Mood predictor error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/premium/sleep-trends', methods=['GET'])
@login_required
def sleep_trends():
    """Тренд сну за останній місяць (Premium feature)."""
    try:
        user = User.query.get(session['user_id'])
        if not user or not user.is_premium:
            return jsonify({
                'status': 'error',
                'message': 'Ця функція доступна тільки для Premium користувачів',
                'premium_required': True
            }), 403

        # Отримуємо дані за останній місяць
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        sleep_entries = MoodEntry.query.filter(
            MoodEntry.user_id == user.id,
            MoodEntry.date >= thirty_days_ago,
            MoodEntry.sleep_hours != None
        ).order_by(MoodEntry.date.asc()).all()

        if not sleep_entries:
            return jsonify({
                'status': 'info',
                'dates': [],
                'hours': [],
                'quality': [],
                'message': 'Недостатньо даних про сон',
                'insights': ['Почни записувати сон, щоб отримати аналіз тренду']
            }), 200

        # Переводимо в графік
        dates = [e.date.strftime('%Y-%m-%d') for e in sleep_entries]
        hours = [e.sleep_hours for e in sleep_entries]
        quality = [e.sleep_quality if e.sleep_quality else 0 for e in sleep_entries]

        # Розраховуємо статистику
        avg_hours = sum(hours) / len(hours)
        avg_quality = sum([q for q in quality if q]) / len([q for q in quality if q]) if any(quality) else 0
        
        # Тренд (перші 2 тижні vs останні 2 тижні)
        mid = len(hours) // 2
        first_half_avg = sum(hours[:mid]) / len(hours[:mid]) if mid > 0 else 0
        second_half_avg = sum(hours[mid:]) / len(hours[mid:]) if len(hours) > mid else 0
        
        trend = "up" if second_half_avg > first_half_avg else "down" if second_half_avg < first_half_avg else "stable"
        trend_percent = abs((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0

        # Генеруємо інсайти
        insights = []
        
        if trend == "up":
            insights.append(f"📈 Ти спиш краще! Твій сон покращився на {trend_percent:.0f}%")
        elif trend == "down":
            insights.append(f"📉 Твій сон трішки зменшився на {trend_percent:.0f}%. Спробуй спати більше!")
        else:
            insights.append(f"➡️ Твій сон стабільний. Середньо: {avg_hours:.1f} годин")

        # Найкращий день
        best_day_idx = hours.index(max(hours))
        worst_day_idx = hours.index(min(hours))
        insights.append(f"🌙 Найбільше спав: {hours[best_day_idx]:.1f} год ({dates[best_day_idx]})")
        insights.append(f"😴 Найменше спав: {hours[worst_day_idx]:.1f} год ({dates[worst_day_idx]})")

        # Якість сну
        if avg_quality > 0:
            if avg_quality >= 3.5:
                insights.append(f"⭐ Якість твого сну чудова: {avg_quality:.1f}/4")
            elif avg_quality >= 2.5:
                insights.append(f"✨ Якість сну у нормі: {avg_quality:.1f}/4")
            else:
                insights.append(f"💤 Спробуй поліпшити якість сну: {avg_quality:.1f}/4")

        return jsonify({
            'status': 'success',
            'dates': dates,
            'hours': hours,
            'quality': quality,
            'average_hours': round(avg_hours, 1),
            'average_quality': round(avg_quality, 1),
            'trend': trend,
            'trend_percent': round(trend_percent, 1),
            'insights': insights
        }), 200

    except Exception as e:
        logging.error(f"Sleep trends error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/premium/activity-recommendations', methods=['GET'])
@login_required
def activity_recommendations():
    """Рекомендації активностей залежно від поточного настрою (Premium feature)."""
    try:
        user = User.query.get(session['user_id'])
        if not user or not user.is_premium:
            return jsonify({
                'status': 'error',
                'message': 'Ця функція доступна тільки для Premium користувачів',
                'premium_required': True
            }), 403

        # Отримуємо параметр настрою або визначаємо з останнього запису користувача
        mood_param = request.args.get('mood')
        
        if not mood_param:
            latest = MoodEntry.query.filter_by(user_id=user.id).order_by(MoodEntry.date.desc()).first()
            current_mood = latest.mood if latest else 'neutral'
        else:
            current_mood = mood_param if mood_param in MoodEntry.VALID_MOODS else 'neutral'

        # База рекомендацій
        recommendations = {
            'happy': {
                'title': 'Ти у чудовому настрої! 🌟',
                'activities': [
                    {'icon': '🎨', 'name': 'Творчість', 'description': 'Малюй, пиши, створюй щось нове!', 'duration': '30-60 хв'},
                    {'icon': '🏃', 'name': 'Активний спорт', 'description': 'Біг, танці, йога — використай енергію!', 'duration': '45 хв'},
                    {'icon': '📞', 'name': 'Зв\'яжися з друзями', 'description': 'Поділись радістю з близькими', 'duration': '20-40 хв'},
                    {'icon': '🎯', 'name': 'Почни новий проект', 'description': 'Ідеальний час для амбітних цілей', 'duration': '1-2 год'},
                    {'icon': '🌳', 'name': 'Прогулянка на природі', 'description': 'Насолоджуйся моментом на свіжому повітрі', 'duration': '30-90 хв'}
                ],
                'tip': 'Використай цю позитивну енергію для справ, які давно відкладав!'
            },
            'neutral': {
                'title': 'Спокійний день 😌',
                'activities': [
                    {'icon': '📚', 'name': 'Почитай книгу', 'description': 'Заглибся в цікаву історію', 'duration': '30-60 хв'},
                    {'icon': '🧘', 'name': 'Медитація', 'description': 'Заспокой розум та знайди баланс', 'duration': '10-20 хв'},
                    {'icon': '🎵', 'name': 'Послухай музику', 'description': 'Створи плейлист під настрій', 'duration': '20-40 хв'},
                    {'icon': '🍳', 'name': 'Приготуй щось смачне', 'description': 'Експериментуй на кухні', 'duration': '45-90 хв'},
                    {'icon': '🎬', 'name': 'Перегляд фільму', 'description': 'Комедія або щось надихаюче', 'duration': '90-120 хв'}
                ],
                'tip': 'Ідеальний час для саморефлексії та спокійних занять'
            },
            'sad': {
                'title': 'Подбай про себе 💙',
                'activities': [
                    {'icon': '🛁', 'name': 'Розслаблююча ванна', 'description': 'Додай аромамасла та музику', 'duration': '20-30 хв'},
                    {'icon': '☕', 'name': 'Улюблений напій', 'description': 'Зроби собі какао або чай', 'duration': '15 хв'},
                    {'icon': '📝', 'name': 'Випиши емоції', 'description': 'Journaling допомагає опрацювати почуття', 'duration': '15-30 хв'},
                    {'icon': '🐾', 'name': 'Час з улюбленцем', 'description': 'Погладь кота/собаку або подивись милі відео', 'duration': '20 хв'},
                    {'icon': '💬', 'name': 'Поговори з близькими', 'description': 'Зателефонуй другу або сім\'ї', 'duration': '30-60 хв'},
                    {'icon': '🌅', 'name': 'Легка прогулянка', 'description': 'Свіже повітря покращує настрій', 'duration': '15-30 хв'}
                ],
                'tip': 'Пам\'ятай: це тимчасово, і ти не одинокий/а. Дозволь собі відчувати емоції'
            }
        }

        result = recommendations.get(current_mood, recommendations['neutral'])
        result['current_mood'] = current_mood
        result['mood_emoji'] = {'happy': '😊', 'neutral': '😐', 'sad': '😢'}.get(current_mood, '❓')

        return jsonify({
            'status': 'success',
            **result
        }), 200

    except Exception as e:
        logging.error(f"Activity recommendations error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== Глобальні Error Handlers ====================

@app.errorhandler(400)
def bad_request(error):
    """Обробка 400 Bad Request"""
    return jsonify({
        'status': 'error',
        'code': 'BAD_REQUEST',
        'message': 'Невалідні дані запиту',
        'details': str(error)
    }), 400


@app.errorhandler(401)
def unauthorized(error):
    """Обробка 401 Unauthorized"""
    return jsonify({
        'status': 'error',
        'code': 'UNAUTHORIZED',
        'message': 'Потрібна авторизація'
    }), 401


@app.errorhandler(403)
def forbidden(error):
    """Обробка 403 Forbidden"""
    return jsonify({
        'status': 'error',
        'code': 'FORBIDDEN',
        'message': 'Доступ заборонено'
    }), 403


@app.errorhandler(404)
def not_found(error):
    """Обробка 404 Not Found"""
    return jsonify({
        'status': 'error',
        'code': 'NOT_FOUND',
        'message': 'Ресурс не знайдено'
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Обробка 405 Method Not Allowed"""
    return jsonify({
        'status': 'error',
        'code': 'METHOD_NOT_ALLOWED',
        'message': 'HTTP метод не дозволений для цього endpoint'
    }), 405


@app.errorhandler(422)
def unprocessable_entity(error):
    """Обробка 422 Unprocessable Entity"""
    return jsonify({
        'status': 'error',
        'code': 'VALIDATION_ERROR',
        'message': 'Дані не пройшли валідацію',
        'details': str(error)
    }), 422


@app.errorhandler(429)
def too_many_requests(error):
    """Обробка 429 Too Many Requests"""
    return jsonify({
        'status': 'error',
        'code': 'RATE_LIMIT_EXCEEDED',
        'message': 'Перевищено ліміт запитів. Спробуйте пізніше'
    }), 429


@app.errorhandler(500)
def internal_server_error(error):
    """Обробка 500 Internal Server Error"""
    logging.error(f"Internal Server Error: {error}")
    return jsonify({
        'status': 'error',
        'code': 'INTERNAL_SERVER_ERROR',
        'message': 'Внутрішня помилка сервера'
    }), 500


@app.errorhandler(503)
def service_unavailable(error):
    """Обробка 503 Service Unavailable"""
    return jsonify({
        'status': 'error',
        'code': 'SERVICE_UNAVAILABLE',
        'message': 'Сервіс тимчасово недоступний'
    }), 503


@app.errorhandler(ValidationError)
def handle_marshmallow_validation(error):
    """Обробка помилок валідації Marshmallow"""
    return jsonify({
        'status': 'error',
        'code': 'VALIDATION_ERROR',
        'message': 'Помилка валідації даних',
        'errors': error.messages
    }), 400


if __name__ == '__main__':
    # Перевіряємо з'єднання з базою даних перед запуском сервера
    if test_db_connection():
        logging.info("Запуск Flask додатку")
        app.run(debug=True)
    else:
        logging.error("Неможливо запустити додаток через помилку з'єднання з базою даних")
        exit(1)