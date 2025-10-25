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

from flask import Flask, render_template, request, jsonify
import time
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from models import db, MoodEntry
from habits_models import Habit, HabitCompletion, MonthlyGoal
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Configure database: use SQLite file in data/ directory
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'data', 'dailymood.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)


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

# Ensure tables exist when the module is imported/run for development
with app.app_context():
    db.create_all()

@app.errorhandler(404)
def not_found_error(error):
    logging.warning(f"404 error: {request.url}")
    return jsonify({
        'status': 'error',
        'message': 'Requested resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    # Log full traceback to help diagnose unexpected server errors
    try:
        tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    except Exception:
        tb = str(error)
    logging.error(f"500 error: {str(error)}\n{tb}")
    # Rollback any active DB transaction to keep session clean
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
    """Log each request."""
    logging.info(f"Request: {request.method} {request.url}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

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

@app.route('/statistics')
def statistics():
    """Render statistics page with recent mood analytics.

    Prepares a small summary (count, most common mood) and a dataset used
    by the frontend Chart.js to render trend and distribution charts.
    The function returns a rendered template with the following context:
    - monthly_entries: int
    - most_common_mood: str
    - mood_data: dict containing dates, values and counts
    """
    # Отримуємо дані за останній місяць — порівнюємо по date() бо MoodEntry.date це Date
    month_ago = (datetime.utcnow() - timedelta(days=30)).date()
    
    # Кількість записів за місяць
    monthly_entries = MoodEntry.query.filter(
        MoodEntry.date >= month_ago
    ).count()

    # Найчастіший настрій (raw key from DB is e.g. 'happy'/'neutral'/'sad')
    most_common = db.session.query(
        MoodEntry.mood,
        func.count(MoodEntry.mood).label('count')
    ).group_by(MoodEntry.mood).order_by(
        func.count(MoodEntry.mood).desc()
    ).first()
    raw_most_common = most_common.mood if most_common else None

    # Helper: translate internal mood keys to Ukrainian labels for display
    def translate_mood_label(key):
        if not key:
            return 'Немає даних'
        mapping = {
            'happy': 'Щасливий',
            'neutral': 'Нейтральний',
            'sad': 'Сумний'
        }
        return mapping.get(key, key)

    most_common_mood = translate_mood_label(raw_most_common)
    
    # Дані для графіків
    entries = MoodEntry.query.filter(
        MoodEntry.date >= month_ago
    ).order_by(MoodEntry.date).all()
    
    mood_data = {
        'dates': [e.date.strftime('%Y-%m-%d') for e in entries],
        'values': [1 if e.mood == 'happy' else 0.5 if e.mood == 'neutral' else 0 for e in entries],
        'moods': ['Щасливий', 'Нейтральний', 'Сумний'],
        'counts': [
            sum(1 for e in entries if e.mood == 'happy'),
            sum(1 for e in entries if e.mood == 'neutral'),
            sum(1 for e in entries if e.mood == 'sad')
        ]
    }
    # Calculate a categorical average mood from numeric mapping and translate
    if mood_data['values']:
        avg_val = sum(mood_data['values']) / len(mood_data['values'])
        # Map average value to nearest category: >0.66 -> happy, >0.33 -> neutral, else sad
        if avg_val > 0.66:
            average_mood = translate_mood_label('happy')
        elif avg_val > 0.33:
            average_mood = translate_mood_label('neutral')
        else:
            average_mood = translate_mood_label('sad')
    else:
        average_mood = '—'

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
                         quotes_count=quotes_count,
                         favorite_quotes_count=favorite_quotes_count,
                         daily_quote=daily_quote,
                         daily_quote_author=daily_quote_author)

@app.route('/api/journal', methods=['GET'])
def list_entries():
    """Return a list of journal entries as JSON.

    Supports optional query params:
    - month: YYYY-MM to filter a specific month
    - mood: filter by mood value (happy, neutral, sad)

    Returns a JSON list of entry dicts using the model's to_dict() helper.
    """
    try:
        month = request.args.get('month')
        mood = request.args.get('mood')
        
        query = MoodEntry.query
        
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
def add_entry():
    """Add a journal entry.

    Expects JSON with at least 'mood', 'date' (ISO YYYY-MM-DD) and 'title'.
    'activities' may be passed as an array and will be stored as a
    comma-separated string in the DB. Returns the created entry JSON on
    success.
    """
    try:
        # Be robust: if client doesn't send JSON, get_json(None) may raise or return None
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({
                'status': 'error',
                'message': 'Невірний формат даних. Очікується JSON з полями: mood, date, title'
            }), 400

        if not all(k in data for k in ['mood', 'date', 'title']):
            return jsonify({
                'status': 'error',
                'message': 'Необхідні поля: mood, date, title'
            }), 400

        try:
            # Convert ISO date string to Python date
            date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            
            # Convert activities list to comma-separated string
            activities = ','.join(data['activities']) if data.get('activities') else None
            
            entry = MoodEntry(
                mood=data['mood'],
                date=date,
                title=data['title'],
                content=data.get('content'),
                activities=activities
            )
            
            db.session.add(entry)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': 'Запис успішно збережено',
                'data': entry.to_dict()
            }), 201
            
        except ValueError as ve:
            return jsonify({
                'status': 'error',
                'message': str(ve)
            }), 400
            
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding entry: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Помилка при збереженні: {str(e)}'
        }), 500

@app.route('/api/journal/<int:entry_id>', methods=['PUT'])
def update_entry(entry_id):
    """Update an existing journal entry."""
    try:
        entry = MoodEntry.query.get_or_404(entry_id)
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
def delete_entry(entry_id):
    """Delete a journal entry."""
    try:
        entry = MoodEntry.query.get_or_404(entry_id)
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


# -------------------- Habits & Goals API --------------------
@app.route('/api/habits', methods=['GET'])
def get_habits():
    try:
        habits = Habit.query.order_by(Habit.id).all()
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
def create_habit():
    try:
        data = request.get_json(silent=True)
        if not data or 'name' not in data or 'type' not in data:
            return jsonify({'status': 'error', 'message': 'Missing habit name or type'}), 400

        habit = Habit(name=data['name'].strip(), type=data['type'])
        db.session.add(habit)
        db.session.commit()
        return jsonify({'status': 'success', 'data': habit.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating habit: {str(e)}")
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


@app.route('/api/goals', methods=['GET'])
def get_goals():
    try:
        goals = MonthlyGoal.query.order_by(MonthlyGoal.deadline).all()
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
        goal = MonthlyGoal(name=data['name'].strip(), deadline=deadline)
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

if __name__ == '__main__':
    # Перевіряємо з'єднання з базою даних перед запуском сервера
    if test_db_connection():
        logging.info("Запуск Flask додатку")
        app.run(debug=True)
    else:
        logging.error("Неможливо запустити додаток через помилку з'єднання з базою даних")
        exit(1)