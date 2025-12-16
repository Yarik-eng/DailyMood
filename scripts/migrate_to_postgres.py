import os
import sys
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker, Session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_sqlite_to_postgres(sqlite_url: str, postgres_url: str):
    """
    Мігрує дані з SQLite до PostgreSQL
    
    Args:
        sqlite_url: SQLite connection string (e.g., sqlite:///data/dailymood.db)
        postgres_url: PostgreSQL connection string (e.g., postgresql://user:pass@localhost/db)
    """
    logger.info("Початок міграції з SQLite до PostgreSQL...")
    
    # Підключення до обох баз
    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(postgres_url)
    
    # Отримання метаданих з SQLite
    sqlite_metadata = MetaData()
    sqlite_metadata.reflect(bind=sqlite_engine)
    
    # Створення схеми в PostgreSQL
    logger.info("Створення схеми в PostgreSQL...")
    postgres_metadata = MetaData()
    postgres_metadata.reflect(bind=postgres_engine)
    
    # Якщо таблиці вже існують, видаляємо їх
    for table_name in reversed(postgres_metadata.sorted_tables):
        logger.info(f"Видалення існуючої таблиці: {table_name}")
        table_name.drop(postgres_engine, checkfirst=True)
    
    # Створюємо таблиці з SQLite метаданих
    sqlite_metadata.create_all(postgres_engine)
    
    # Створення сесій
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)
    
    sqlite_session = SQLiteSession()
    postgres_session = PostgresSession()
    
    try:
        # Міграція даних по кожній таблиці
        for table_name in sqlite_metadata.tables.keys():
            logger.info(f"Міграція таблиці: {table_name}")
            
            table = Table(table_name, sqlite_metadata, autoload_with=sqlite_engine)
            
            # Отримання всіх записів з SQLite
            sqlite_conn = sqlite_engine.connect()
            rows = sqlite_conn.execute(table.select()).fetchall()
            
            if rows:
                logger.info(f"Знайдено {len(rows)} записів в таблиці {table_name}")
                
                # Вставка в PostgreSQL
                postgres_conn = postgres_engine.connect()
                for row in rows:
                    insert_stmt = table.insert().values(**row._mapping)
                    postgres_conn.execute(insert_stmt)
                postgres_conn.commit()
                postgres_conn.close()
                
                logger.info(f"Успішно мігровано {len(rows)} записів")
            else:
                logger.info(f"Таблиця {table_name} пуста")
            
            sqlite_conn.close()
        
        postgres_session.commit()
        logger.info("✅ Міграція завершена успішно!")
        
        # Виведення статистики
        logger.info("\n=== Статистика міграції ===")
        for table_name in sqlite_metadata.tables.keys():
            table = Table(table_name, postgres_metadata, autoload_with=postgres_engine)
            postgres_conn = postgres_engine.connect()
            count = postgres_conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).scalar()
            postgres_conn.close()
            logger.info(f"{table_name}: {count} записів")
        
    except Exception as e:
        logger.error(f"❌ Помилка під час міграції: {e}")
        postgres_session.rollback()
        raise
    finally:
        sqlite_session.close()
        postgres_session.close()

def main():
    # Отримання параметрів з аргументів командного рядка або з .env
    sqlite_url = os.getenv('SQLITE_URL', 'sqlite:///data/dailymood.db')
    postgres_url = os.getenv('DATABASE_URL')
    
    if not postgres_url:
        logger.error("❌ DATABASE_URL не встановлено!")
        logger.info("Встановіть змінну оточення DATABASE_URL або передайте як аргумент")
        logger.info("Приклад: DATABASE_URL=postgresql://user:pass@localhost/dailymood python migrate_to_postgres.py")
        sys.exit(1)
    
    logger.info(f"SQLite URL: {sqlite_url}")
    logger.info(f"PostgreSQL URL: {postgres_url.replace(postgres_url.split('@')[0].split('//')[1], '***')}")
    
    confirm = input("\n⚠️  УВАГА: Ця операція видалить всі існуючі дані в PostgreSQL БД!\nПродовжити? (yes/no): ")
    
    if confirm.lower() != 'yes':
        logger.info("Міграцію скасовано")
        sys.exit(0)
    
    try:
        migrate_sqlite_to_postgres(sqlite_url, postgres_url)
    except Exception as e:
        logger.error(f"Міграція не вдалася: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
