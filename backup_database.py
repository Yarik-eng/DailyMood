#!/usr/bin/env python3
"""
Скрипт для резервного копіювання бази даних
Використання: python backup_database.py
"""

import os
import shutil
from datetime import datetime

DB_PATH = './data/dailymood.db'
BACKUP_DIR = './data/backups'

def create_backup():
    """Створити резервну копію бази даних"""
    print("=" * 60)
    print("💾 РЕЗЕРВНЕ КОПІЮВАННЯ БАЗИ ДАНИХ")
    print("=" * 60)
    print()
    
    # Перевірка існування бази
    if not os.path.exists(DB_PATH):
        print(f"❌ База даних не знайдена: {DB_PATH}")
        print("Спочатку запустіть додаток для створення бази даних")
        return False
    
    # Створення папки для бекапів
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Генерація імені файлу з поточною датою та часом
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'dailymood_backup_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    # Копіювання файлу
    try:
        file_size = os.path.getsize(DB_PATH)
        print(f"📁 Оригінальний файл: {DB_PATH}")
        print(f"📦 Розмір: {file_size:,} байт ({file_size/1024:.2f} KB)")
        print()
        print(f"🔄 Копіювання до: {backup_path}")
        
        shutil.copy2(DB_PATH, backup_path)
        
        # Перевірка успішності
        if os.path.exists(backup_path):
            backup_size = os.path.getsize(backup_path)
            print()
            print("✅ Резервна копія успішно створена!")
            print(f"📁 Місцезнаходження: {backup_path}")
            print(f"📦 Розмір: {backup_size:,} байт ({backup_size/1024:.2f} KB)")
            
            # Список всіх бекапів
            print()
            print("📚 Всі резервні копії:")
            backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')])
            
            total_size = 0
            for i, backup in enumerate(backups, 1):
                backup_full_path = os.path.join(BACKUP_DIR, backup)
                size = os.path.getsize(backup_full_path)
                mtime = datetime.fromtimestamp(os.path.getmtime(backup_full_path))
                total_size += size
                
                is_current = "👈 Щойно створений" if backup == backup_filename else ""
                print(f"  {i}. {backup}")
                print(f"     Дата: {mtime.strftime('%Y-%m-%d %H:%M:%S')} | Розмір: {size/1024:.2f} KB {is_current}")
            
            print()
            print(f"💾 Загальний розмір всіх бекапів: {total_size/1024:.2f} KB ({total_size/1024/1024:.2f} MB)")
            
            return True
        else:
            print("❌ Помилка при створенні резервної копії")
            return False
            
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return False


def restore_backup(backup_filename=None):
    """Відновити базу даних з резервної копії"""
    print()
    print("=" * 60)
    print("♻️  ВІДНОВЛЕННЯ З РЕЗЕРВНОЇ КОПІЇ")
    print("=" * 60)
    print()
    
    if not os.path.exists(BACKUP_DIR):
        print(f"❌ Папка з бекапами не знайдена: {BACKUP_DIR}")
        return False
    
    # Список доступних бекапів
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')], reverse=True)
    
    if not backups:
        print("❌ Резервних копій не знайдено")
        return False
    
    print("📚 Доступні резервні копії:")
    for i, backup in enumerate(backups, 1):
        backup_full_path = os.path.join(BACKUP_DIR, backup)
        size = os.path.getsize(backup_full_path)
        mtime = datetime.fromtimestamp(os.path.getmtime(backup_full_path))
        print(f"  {i}. {backup}")
        print(f"     Дата: {mtime.strftime('%Y-%m-%d %H:%M:%S')} | Розмір: {size/1024:.2f} KB")
    
    print()
    print("⚠️  УВАГА: Відновлення перезапише поточну базу даних!")
    print()
    
    if backup_filename is None:
        try:
            choice = input(f"Введіть номер бекапу (1-{len(backups)}) або 'q' для виходу: ").strip()
            
            if choice.lower() == 'q':
                print("Відновлення скасовано")
                return False
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(backups):
                backup_filename = backups[choice_num - 1]
            else:
                print("❌ Невірний вибір")
                return False
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Відновлення скасовано")
            return False
    
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    if not os.path.exists(backup_path):
        print(f"❌ Файл бекапу не знайдено: {backup_path}")
        return False
    
    # Створення бекапу поточної бази перед відновленням
    if os.path.exists(DB_PATH):
        temp_backup = DB_PATH + '.before_restore'
        shutil.copy2(DB_PATH, temp_backup)
        print(f"📋 Створено тимчасову копію поточної бази: {temp_backup}")
    
    try:
        print(f"🔄 Відновлення з {backup_filename}...")
        shutil.copy2(backup_path, DB_PATH)
        
        print("✅ База даних успішно відновлена!")
        print(f"📁 Відновлено з: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка при відновленні: {e}")
        
        # Спроба відновити попередню версію
        temp_backup = DB_PATH + '.before_restore'
        if os.path.exists(temp_backup):
            try:
                shutil.copy2(temp_backup, DB_PATH)
                print("♻️  Відновлено попередню версію бази даних")
            except:
                print("⚠️  Не вдалося відновити попередню версію")
        
        return False


def clean_old_backups(keep_last=10):
    """Видалити старі бекапи, залишивши тільки останні N"""
    print()
    print("=" * 60)
    print("🧹 ОЧИЩЕННЯ СТАРИХ БЕКАПІВ")
    print("=" * 60)
    print()
    
    if not os.path.exists(BACKUP_DIR):
        print("❌ Папка з бекапами не знайдена")
        return
    
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')])
    
    if len(backups) <= keep_last:
        print(f"✅ Всього {len(backups)} бекапів. Очищення не потрібне (зберігаємо {keep_last})")
        return
    
    backups_to_delete = backups[:-keep_last]
    
    print(f"📊 Знайдено {len(backups)} бекапів")
    print(f"🗑️  Буде видалено {len(backups_to_delete)} старих бекапів")
    print()
    
    total_freed = 0
    for backup in backups_to_delete:
        backup_path = os.path.join(BACKUP_DIR, backup)
        size = os.path.getsize(backup_path)
        try:
            os.remove(backup_path)
            print(f"  ✅ Видалено: {backup} ({size/1024:.2f} KB)")
            total_freed += size
        except Exception as e:
            print(f"  ❌ Помилка при видаленні {backup}: {e}")
    
    print()
    print(f"💾 Звільнено місця: {total_freed/1024:.2f} KB ({total_freed/1024/1024:.2f} MB)")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'restore':
            restore_backup()
        elif command == 'clean':
            keep = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            clean_old_backups(keep)
        elif command == 'backup':
            create_backup()
        else:
            print("Використання:")
            print("  python backup_database.py            - Створити бекап")
            print("  python backup_database.py backup     - Створити бекап")
            print("  python backup_database.py restore    - Відновити з бекапу")
            print("  python backup_database.py clean [N]  - Видалити старі бекапи (залишити N)")
    else:
        # За замовчуванням створюємо бекап
        create_backup()
        
        print()
        print("💡 КОРИСНІ КОМАНДИ:")
        print("  • Відновити з бекапу:    python backup_database.py restore")
        print("  • Очистити старі бекапи: python backup_database.py clean 5")
        print()
