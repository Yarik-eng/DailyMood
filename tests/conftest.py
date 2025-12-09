"""
Pytest конфігурація та фіксчури для тестування DailyMood додатку.
"""

import pytest
import tempfile
import os
from app import app, db
from models import User, Feedback


@pytest.fixture(scope='function')
def app_with_db():
    """Налаштовує Flask додаток з тестовою БД для кожного тесту."""
    # Створюємо тимчасовий файл для тестової БД
    db_fd, db_path = tempfile.mkstemp()
    
    # Налаштовуємо додаток
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    # Створюємо контекст
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    
    # Очищуємо файл
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app_with_db):
    """Flask тестовий клієнт для відправки запитів."""
    return app_with_db.test_client()


@pytest.fixture
def test_user(app_with_db):
    """Створити тестового користувача для тестів."""
    with app_with_db.app_context():
        user = User(email='user@test.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()  # Флаш щоб дати ID, але не закривати сесію
        user_id = user.id
        user_email = user.email
        user_password_hash = user.password_hash
    
    # Повертаємо лише потрібні дані, не сам об'єкт
    class UserStub:
        def __init__(self, id, email, password_hash):
            self.id = id
            self.email = email
            self.password_hash = password_hash
        
        def check_password(self, password):
            from werkzeug.security import check_password_hash
            return check_password_hash(self.password_hash, password)
        
        def to_dict(self):
            return {
                'id': self.id,
                'email': self.email,
                'is_admin': False,
                'is_premium': False,
                'created_at': None,
                'premium_started_at': None,
                'premium_expires_at': None,
                'avatar': None
            }
    
    return UserStub(user_id, user_email, user_password_hash)


@pytest.fixture
def admin_user(app_with_db):
    """Створити адмін-користувача для тестів."""
    with app_with_db.app_context():
        user = User(email='admin@test.com', is_admin=True)
        user.set_password('adminpass123')
        db.session.add(user)
        db.session.flush()
        user_id = user.id
    
    class AdminStub:
        def __init__(self, id):
            self.id = id
    
    return AdminStub(user_id)


@pytest.fixture
def logged_in_client(client, test_user):
    """Flask клієнт з залогованим користувачем."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
    return client


@pytest.fixture
def logged_in_admin_client(client, admin_user):
    """Flask клієнт з залогованим адміном."""
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
    return client


# ---- Фіксчури для інтеграційних тестів (потрібні справжні записи в БД) ----
@pytest.fixture
def real_user(app_with_db):
    """Справжній користувач у тестовій БД (для інтеграційних тестів)."""
    with app_with_db.app_context():
        user = User(email='user@test.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id  # Зберігаємо id щоб уникнути DetachedInstanceError
    return user_id


@pytest.fixture
def real_admin(app_with_db):
    """Справжній адмін у тестовій БД (для інтеграційних тестів)."""
    with app_with_db.app_context():
        user = User(email='admin@test.com', is_admin=True)
        user.set_password('adminpass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    return user_id


@pytest.fixture
def logged_in_client_db(client, real_user):
    """Клієнт з сесією реального користувача (рядок є в БД)."""
    with client.session_transaction() as sess:
        sess['user_id'] = real_user
    return client


@pytest.fixture
def logged_in_admin_client_db(client, real_admin):
    """Клієнт з сесією реального адміна (рядок є в БД)."""
    with client.session_transaction() as sess:
        sess['user_id'] = real_admin
    return client
