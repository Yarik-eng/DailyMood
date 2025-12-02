"""
Інтерактивне видалення тестових даних
Використання: python cleanup_test_orders.py


ВАЖЛИВО:ЗАПУСКАТИ ТОДІ КОЛИ ЗУПИНЕННО ВСІ СЕРВІСИ, ЩО ПРАЦЮЮТЬ З БАЗОЮ ДАНИХ!

КОМАНДА: .venv\Scripts\python.exe cleanup_database.py
"""
from app import app, db
from models import Order, Payment, OrderItem, Feedback, MoodEntry, User
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import time

# Мапа доступних моделей
MODELS = {
    'order': {'model': Order, 'name': 'Замовлення', 'icon': '📦'},
    'payment': {'model': Payment, 'name': 'Платежі', 'icon': '💳'},
    'feedback': {'model': Feedback, 'name': 'Відгуки', 'icon': '💬'},
    'mood': {'model': MoodEntry, 'name': 'Записи настрою', 'icon': '📝'},
    'user': {'model': User, 'name': 'Користувачі', 'icon': '👤'}
}

def show_menu():
    """Показати меню вибору"""
    print("\n" + "="*50)
    print("🗑️  ВИДАЛЕННЯ ТЕСТОВИХ ДАНИХ")
    print("="*50)
    print("\nДоступні моделі:")
    for key, info in MODELS.items():
        with app.app_context():
            count = info['model'].query.count()
        print(f"  {info['icon']} {key:10} - {info['name']} (всього: {count})")
    print("\n  ❌ exit       - Вийти")
    print("="*50)

def _exec_with_retry(fn, *, retries=3, delay=1.0):
    """Execute a function with simple retry on SQLite lock."""
    attempt = 0
    while True:
        try:
            return fn()
        except OperationalError as e:
            msg = str(e).lower()
            if ("database is locked" in msg or "database is busy" in msg) and attempt < retries:
                attempt += 1
                print(f"⏳ База зайнята, повтор {attempt}/{retries} через {delay}s...")
                time.sleep(delay)
                continue
            raise

def delete_by_range(model_key, start_id, end_id, chunk_size=200):
    """Видалити записи з діапазону ID"""
    if model_key not in MODELS:
        print(f"❌ Модель '{model_key}' не знайдена!")
        return
    
    model_info = MODELS[model_key]
    Model = model_info['model']
    
    with app.app_context():
        # Зібрати усі ID до видалення
        ids = [row.id for row in Model.query.filter(Model.id >= start_id, Model.id <= end_id).all()]
        total = len(ids)
        if total == 0:
            print("❕ Нічого не знайдено у вказаному діапазоні")
            return

        print(f"🔍 Знайдено {total} записів для видалення")
        deleted = 0

        # Видалення по шматках
        for i in range(0, total, chunk_size):
            batch = ids[i:i+chunk_size]

            # локальний цикл ретраїв з обов'язковим rollback на помилці
            attempts, max_attempts, delay = 0, 5, 2.0
            while True:
                try:
                    if model_key == 'order':
                        orders = Order.query.filter(Order.id.in_(batch)).all()
                        for order in orders:
                            if order.payment:
                                db.session.delete(order.payment)
                            for item in order.items:
                                db.session.delete(item)
                            db.session.delete(order)
                    else:
                        db.session.query(Model).filter(Model.id.in_(batch)).delete(synchronize_session=False)
                    db.session.commit()
                    break
                except OperationalError as e:
                    db.session.rollback()
                    attempts += 1
                    if attempts >= max_attempts:
                        raise
                    print(f"⏳ База зайнята, повтор {attempts}/{max_attempts} через {delay}s...")
                    time.sleep(delay)
                    delay = min(delay * 1.5, 10.0)

            deleted += len(batch)
            print(f"   ✔️  Коміт: видалено {deleted}/{total}")

        print(f"\n✅ Видалено {deleted} {model_info['name']} (ID {start_id}-{end_id})")
        remaining = Model.query.count()
        print(f"📊 Залишилось {model_info['name']}: {remaining}")

def main():
    """Головна функція"""
    with app.app_context():
        # Покращення конкурентності для SQLite
        try:
            db.session.execute(text("PRAGMA journal_mode=WAL"))
            db.session.execute(text("PRAGMA busy_timeout=30000"))
            db.session.commit()
            print("⚙️  Увімкнено WAL та busy_timeout=30s")
        except Exception:
            # Якщо не вдалося застосувати, продовжуємо без цього
            pass
        while True:
            show_menu()
            
            # Отримати команду від користувача
            user_input = input("\n💬 Введіть команду (наприклад: feedback 15-6000): ").strip().lower()
            
            if user_input == 'exit':
                print("👋 До побачення!")
                break
            
            # Парсинг команди
            parts = user_input.split()
            if len(parts) != 2:
                print("❌ Неправильний формат! Приклад: feedback 15-6000")
                continue
            
            model_key = parts[0]
            id_range = parts[1]
            
            # Парсинг діапазону ID
            if '-' not in id_range:
                print("❌ Неправильний діапазон! Використовуйте формат: 15-6000")
                continue
            
            try:
                start_id, end_id = map(int, id_range.split('-'))
                if start_id > end_id:
                    print("❌ Початковий ID повинен бути менше кінцевого!")
                    continue
            except ValueError:
                print("❌ ID повинні бути числами!")
                continue
            
            # Підтвердження
            model_info = MODELS.get(model_key)
            if model_info:
                confirm = input(f"⚠️  Видалити {model_info['name']} з ID {start_id} до {end_id}? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y', 'так', 'т']:
                    delete_by_range(model_key, start_id, end_id)
                else:
                    print("❌ Скасовано")
            else:
                print(f"❌ Модель '{model_key}' не знайдена!")

if __name__ == '__main__':
    main()
