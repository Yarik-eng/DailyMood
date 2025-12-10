"""
Скрипт для створення адміністратора DailyMood та базових продуктів.

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
from models import User, Product

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


def create_sample_products():
    """Створити базові продукти для магазину."""
    with app.app_context():
        # Перевіряємо чи вже існують продукти
        if Product.query.count() > 0:
            print('\n✅ Продукти вже існують у базі.')
            return
        
        sample_products = [
            {
                'name': 'Премиум підписка',
                'slug': 'premium-subscription',
                'type': 'premium',
                'description': 'Розблокуйте всі преміум-функції на 1 місяць',
                'price': 99.99
            },
            {
                'name': 'Мотиваційні цитати',
                'slug': 'motivation-quotes',
                'type': 'quote_pack',
                'description': 'Збірка 500+ мотиваційних цитат',
                'price': 9.99
            },
            {
                'name': 'Тема Ніч',
                'slug': 'dark-theme',
                'type': 'theme',
                'description': 'Темна тема для комфортного використання вночі',
                'price': 4.99
            },
            {
                'name': 'Шаблон планування',
                'slug': 'planning-template',
                'type': 'journal_template',
                'description': 'Готові шаблони для планування дня',
                'price': 2.99
            }
        ]
        
        for product_data in sample_products:
            product = Product(**product_data)
            db.session.add(product)
        
        db.session.commit()
        print(f'\n✅ Створено {len(sample_products)} базових продуктів:')
        for p in sample_products:
            print(f'   - {p["name"]} ({p["slug"]}) - {p["price"]} грн')

if __name__ == '__main__':
    print('🔧 Створення адміністратора DailyMood...\n')
    
    import argparse
    parser = argparse.ArgumentParser(description='Створити адміністратора DailyMood')
    parser.add_argument('--email', default='admin@dailymood.com', help='Email адміна (за замовчуванням: admin@dailymood.com)')
    parser.add_argument('--password', default='admin123', help='Пароль адміна (за замовчуванням: admin123)')
    
    args = parser.parse_args()
    
    print(f'Email: {args.email}')
    print(f'Пароль: {args.password}\n')
    
    create_admin(args.email, args.password)
    create_sample_products()
    
    print('\n💡 Тепер ви можете увійти через /auth/login')
