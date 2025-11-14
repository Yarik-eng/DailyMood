"""
Скрипт для створення адміністратора DailyMood.

Використання:
    python scripts/create_admin.py

За замовчуванням створює адміна з email: admin@dailymood.com та паролем: admin123
Якщо користувач з таким email вже існує, він буде оновлений (встановлено is_admin=True).
"""

import sys
import os

# Додаємо батьківську папку до sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User

def create_admin(email='admin@dailymood.com', password='admin123'):
    """
    Створити адмін-користувача або оновити існуючого.
    
    Args:
        email: Email адміністратора
        password: Пароль (мінімум 6 символів)
    """
    with app.app_context():
        # Перевіряємо довжину паролю
        if len(password) < 6:
            print('❌ Помилка: пароль повинен містити мінімум 6 символів')
            return
        
        # Шукаємо існуючого користувача
        user = User.query.filter_by(email=email.lower()).first()
        
        if user:
            # Оновити існуючого користувача
            user.is_admin = True
            user.set_password(password)
            db.session.commit()
            print(f'✅ Користувач {email} оновлено як адмін.')
        else:
            # Створити нового
            user = User(email=email.lower(), is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f'✅ Адмін-користувач {email} створено успішно!')
            print(f'   Email: {email}')
            print(f'   Пароль: {password}')
            print(f'   is_admin: True')

if __name__ == '__main__':
    print('🔧 Створення адміністратора DailyMood...\n')
    
    # Можна передати email та пароль як аргументи
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
        create_admin(email, password)
    else:
        print('Використовуються стандартні credentials:')
        print('Email: admin@dailymood.com')
        print('Пароль: admin123\n')
        create_admin()
    
    print('\n💡 Тепер ви можете увійти через /auth/login')
