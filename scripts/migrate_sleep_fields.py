#!/usr/bin/env python3
"""
Скрипт для додавання полів sleep_quality та sleep_hours до таблиці mood_entries
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from models import MoodEntry
from sqlalchemy import inspect, text

def migrate_sleep_fields():
    """Додає поля sleep_quality та sleep_hours до mood_entries таблиці"""
    
    with app.app_context():
        # Перевіримо чи існують поля
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('mood_entries')]
        
        print(f"Існуючи колонки: {columns}")
        
        # Додаємо sleep_quality якщо не існує
        if 'sleep_quality' not in columns:
            print("Додавання колонки sleep_quality...")
            with db.engine.begin() as connection:
                connection.execute(text('ALTER TABLE mood_entries ADD COLUMN sleep_quality INTEGER'))
            print("✓ sleep_quality додана")
        else:
            print("✓ sleep_quality вже існує")
        
        # Додаємо sleep_hours якщо не існує
        if 'sleep_hours' not in columns:
            print("Додавання колонки sleep_hours...")
            with db.engine.begin() as connection:
                connection.execute(text('ALTER TABLE mood_entries ADD COLUMN sleep_hours FLOAT'))
            print("✓ sleep_hours додана")
        else:
            print("✓ sleep_hours вже існує")
        
        # Коммітимо зміни
        db.session.commit()
        print("\n✓ Міграція завершена успішно!")

if __name__ == '__main__':
    try:
        migrate_sleep_fields()
    except Exception as e:
        print(f"✗ Помилка під час міграції: {e}")
        sys.exit(1)
