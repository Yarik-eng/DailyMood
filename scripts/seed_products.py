"""
Seed script to populate the database with initial products.
Run this once to add Premium subscription and sample products.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Product

def seed_products():
    """Create initial products in the database."""
    with app.app_context():
        # Check if products already exist
        existing = Product.query.count()
        if existing > 0:
            print(f"⚠️  База вже містить {existing} продуктів. Пропускаємо створення.")
            print("Якщо хочете перестворити, видаліть спочатку існуючі продукти.")
            return

        products_data = [
            {
                'name': 'Premium підписка',
                'slug': 'premium-subscription',
                'type': 'subscription',
                'description': 'Отримайте доступ до всіх преміум-функцій: Mood Predictor, Activity Recommendations, додаткові теми та аватари.',
                'price': 99.00,
                'is_active': True
            },
            {
                'name': 'Пакет мотиваційних цитат',
                'slug': 'motivation-quotes-pack',
                'type': 'quote_pack',
                'description': '100+ ексклюзивних мотиваційних цитат для щоденного натхнення.',
                'price': 29.00,
                'is_active': True
            },
            {
                'name': 'Тема "Океан спокою"',
                'slug': 'ocean-theme',
                'type': 'theme',
                'description': 'Заспокійлива синя тема з морськими акцентами для вашого щоденника.',
                'price': 19.00,
                'is_active': True
            },
            {
                'name': 'Шаблон щоденника "Подорожі"',
                'slug': 'travel-journal-template',
                'type': 'journal_template',
                'description': 'Готовий шаблон для фіксації ваших подорожей та вражень.',
                'price': 25.00,
                'is_active': True
            },
            {
                'name': 'Курс "21 день продуктивності"',
                'slug': 'productivity-course',
                'type': 'habit_course',
                'description': 'Покроковий курс для формування продуктивних звичок за 21 день.',
                'price': 149.00,
                'is_active': True
            }
        ]

        created_count = 0
        for product_data in products_data:
            # Check if this slug already exists
            existing_product = Product.query.filter_by(slug=product_data['slug']).first()
            if existing_product:
                print(f"⚠️  Продукт '{product_data['name']}' вже існує. Пропускаємо.")
                continue

            product = Product(**product_data)
            db.session.add(product)
            created_count += 1
            print(f"✅ Створено: {product_data['name']} ({product_data['price']} грн)")

        if created_count > 0:
            db.session.commit()
            print(f"\n🎉 Успішно додано {created_count} продуктів у базу даних!")
        else:
            print("\n✨ Всі продукти вже існують.")

if __name__ == '__main__':
    print("🌱 Початок заповнення бази продуктами...\n")
    try:
        seed_products()
    except Exception as e:
        print(f"\n❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
