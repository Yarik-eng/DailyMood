#!/usr/bin/env python3
"""
Скрипт для перевірки збереження даних в Docker контейнері
Використання: python test_data_persistence.py
"""

import os
import sqlite3
from datetime import datetime

DB_PATH = './data/dailymood.db'

def check_database():
    """Перевірка чи існує база даних та її стан"""
    print("=" * 60)
    print("🔍 ПЕРЕВІРКА ЗБЕРЕЖЕННЯ БАЗИ ДАНИХ")
    print("=" * 60)
    
    # Перевірка існування файлу
    if not os.path.exists(DB_PATH):
        print(f"❌ База даних НЕ знайдена: {DB_PATH}")
        print("Створіть базу даних запустивши додаток")
        return False
    
    # Інформація про файл
    file_size = os.path.getsize(DB_PATH)
    file_mtime = datetime.fromtimestamp(os.path.getmtime(DB_PATH))
    
    print(f"✅ База даних знайдена: {DB_PATH}")
    print(f"📦 Розмір: {file_size:,} байт ({file_size/1024:.2f} KB)")
    print(f"📅 Остання зміна: {file_mtime}")
    print()
    
    # Підключення до бази
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Перевірка таблиць
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"📊 Знайдено таблиць: {len(tables)}")
        print("Список таблиць:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  • {table_name}: {count} записів")
        
        print()
        
        # Детальна статистика по користувачам
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
        premium_count = cursor.fetchone()[0]
        
        print("👥 КОРИСТУВАЧІ:")
        print(f"  Всього: {users_count}")
        print(f"  Адмінів: {admin_count}")
        print(f"  Premium: {premium_count}")
        
        if users_count > 0:
            cursor.execute("SELECT id, email, is_admin, is_premium FROM users LIMIT 5")
            users = cursor.fetchall()
            print("\n  Список користувачів (перші 5):")
            for user in users:
                uid, email, is_admin, is_premium = user
                badges = []
                if is_admin:
                    badges.append("👑 Admin")
                if is_premium:
                    badges.append("⭐ Premium")
                badge_str = " " + " ".join(badges) if badges else ""
                print(f"    #{uid}: {email}{badge_str}")
        
        print()
        
        # Статистика по записам щоденника
        cursor.execute("SELECT COUNT(*) FROM mood_entries")
        entries_count = cursor.fetchone()[0]
        
        print("📔 ЩОДЕННИК:")
        print(f"  Всього записів: {entries_count}")
        
        if entries_count > 0:
            cursor.execute("""
                SELECT mood, COUNT(*) as cnt 
                FROM mood_entries 
                GROUP BY mood 
                ORDER BY cnt DESC
            """)
            moods = cursor.fetchall()
            print("  Розподіл настрою:")
            for mood, cnt in moods:
                print(f"    {mood}: {cnt}")
        
        print()
        
        # Продукти
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        active_products = cursor.fetchone()[0]
        
        print("🛍️ МАГАЗИН:")
        print(f"  Всього продуктів: {products_count}")
        print(f"  Активних: {active_products}")
        
        if products_count > 0:
            cursor.execute("SELECT id, name, price, type FROM products WHERE is_active = 1 LIMIT 5")
            products = cursor.fetchall()
            print("\n  Активні продукти:")
            for prod in products:
                pid, name, price, ptype = prod
                print(f"    #{pid}: {name} - ${price} ({ptype})")
        
        print()
        
        # Замовлення
        cursor.execute("SELECT COUNT(*) FROM orders")
        orders_count = cursor.fetchone()[0]
        
        print("📦 ЗАМОВЛЕННЯ:")
        print(f"  Всього: {orders_count}")
        
        if orders_count > 0:
            cursor.execute("""
                SELECT status, COUNT(*) as cnt 
                FROM orders 
                GROUP BY status
            """)
            statuses = cursor.fetchall()
            print("  По статусах:")
            for status, cnt in statuses:
                print(f"    {status}: {cnt}")
        
        conn.close()
        
        print()
        print("=" * 60)
        print("✅ База даних працює коректно!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка при роботі з базою: {e}")
        return False


def test_persistence():
    """Тест збереження даних"""
    print("\n" + "=" * 60)
    print("🧪 ТЕСТ ЗБЕРЕЖЕННЯ ДАНИХ")
    print("=" * 60)
    print()
    print("ℹ️  Цей скрипт перевіряє чи зберігаються дані між перезапусками")
    print()
    print("📝 Інструкція:")
    print("1. Запустіть цей скрипт ПЕРЕД перезапуском контейнера")
    print("2. Запам'ятайте кількість записів")
    print("3. Перезапустіть контейнер: docker compose restart")
    print("4. Запустіть скрипт ПІСЛЯ перезапуску")
    print("5. Якщо кількість записів та дата зміни файлу ОДНАКОВІ - дані зберігаються! ✅")
    print()


if __name__ == '__main__':
    test_persistence()
    check_database()
    
    print()
    print("💡 КОРИСНІ КОМАНДИ:")
    print("  • Перезапустити Docker:  docker compose restart")
    print("  • Переборудити образ:    docker compose up --build")
    print("  • Зупинити (БЕЗ видалення даних): docker compose down")
    print("  • Видалити ВСЕ (включно з даними): docker compose down -v")
    print()
