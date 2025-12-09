"""
Integration тести для API ендпоінтів DailyMood додатку.

Integration тест = тестуємо ЦІЛИЙ ланцюг:
1. Відправляємо HTTP запит
2. Flask обробляє його
3. БД зберігає/повертає дані
4. Перевіяємо відповідь

Це більш реалістично, ніж unit тести!
"""

import pytest
import json
from app import db
from models import User, Feedback


class TestAuthAPI:
    """Integration тести для авторизації (логін, реєстрація)."""
    
    def test_register_success(self, client, app_with_db):
        """
        ТЕСТ 1: Успішна реєстрація нового користувача.
        
        ЩО РОБИМО:
        1. Відправляємо POST запит до /auth/register
        2. Передаємо email та пароль
        3. Перевіяємо что повертається 201 (створено)
        4. Перевіяємо що в відповіді є дані користувача
        
        ЧОМУ ТАК:
        - Це реальний сценарій: користувач приходить на сайт, реєструється
        - Тестуємо весь ланцюг: API → Flask → БД → відповідь
        """
        response = client.post('/auth/register',
            json={
                'email': 'newuser@example.com',
                'password': 'securepass123'
            },
            content_type='application/json'
        )
        
        # Перевіяємо статус код
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        
        # Перевіяємо дані відповіді
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'user' in data
        assert data['user']['email'] == 'newuser@example.com'
        
        # Перевіяємо що користувач насправді в БД
        with app_with_db.app_context():
            user = User.query.filter_by(email='newuser@example.com').first()
            assert user is not None
            assert user.email == 'newuser@example.com'
    
    def test_register_short_password(self, client):
        """
        ТЕСТ 2: Реєстрація з коротким паролем відхиляється.
        
        ЩО РОБИМО:
        1. Пароль менше 6 символів (неправильно)
        2. Відправляємо запит
        3. Перевіяємо що повертається 400 (помилка)
        4. Користувач НЕ створюється
        
        ЧОМУ ТАК:
        - Система повинна валідувати пароль
        - Коротке пароль = слабкий пароль = небезпека
        """
        response = client.post('/auth/register',
            json={
                'email': 'user@example.com',
                'password': '123'  # Тільки 3 символи!
            },
            content_type='application/json'
        )
        
        # Перевіяємо що запит відхилено
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data['message'] or 'Пароль' in data['message']
    
    def test_login_success(self, client, real_user, app_with_db):
        """
        ТЕСТ 3: Успішний логін.
        
        ЩО РОБИМО:
        1. Маємо користувача test_user (email: user@test.com, пароль: password123)
        2. Відправляємо POST /auth/login з правильними даними
        3. Перевіяємо що повертається 200
        4. Перевіяємо що в відповіді є дані користувача
        
        ЧОМУ ТАК:
        - Це основна операція: користувач входить на сайт
        - Тестуємо що пароль перевіряється правильно
        """
        response = client.post('/auth/login',
            json={
                'email': 'user@test.com',
                'password': 'password123'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'user' in data
        assert data['user']['email'] == 'user@test.com'
    
    def test_login_wrong_password(self, client, test_user):
        """
        ТЕСТ 4: Логін з неправильним паролем відхиляється.
        
        ЩО РОБИМО:
        1. Користувач test_user має пароль 'password123'
        2. Намагаємось залогінитись з 'wrongpassword'
        3. Перевіяємо що повертається 401 (не авторизований)
        
        ЧОМУ ТАК:
        - Безпека: неправильний пароль = відмова в доступі
        """
        response = client.post('/auth/login',
            json={
                'email': 'user@test.com',
                'password': 'wrongpassword'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'


class TestFeedbackAPI:
    """Integration тести для API відгуків."""
    
    def test_create_feedback_success(self, client, app_with_db):
        """
        ТЕСТ 5: Успішне створення відгука.
        
        ЩО РОБИМО:
        1. Відправляємо POST /api/feedback з даними
        2. Перевіяємо що повертається 200
        3. Перевіяємо що відгук збережено в БД
        
        ЧОМУ ТАК:
        - Користувачі залишають відгуки, ми повинні їх зберігати
        """
        response = client.post('/api/feedback',
            json={
                'name': 'Alice',
                'email': 'alice@example.com',
                'message': 'Amazing app!',
                'rating': 5
            },
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'data' in data
        assert data['data']['name'] == 'Alice'
        assert data['data']['rating'] == 5
        
        # Перевіяємо що в БД зберігся
        with app_with_db.app_context():
            feedback = Feedback.query.filter_by(email='alice@example.com').first()
            assert feedback is not None
            assert feedback.message == 'Amazing app!'
    
    def test_list_feedback(self, client, app_with_db):
        """
        ТЕСТ 6: Отримання списку відгуків.
        
        ЩО РОБИМО:
        1. Створюємо кілька відгуків
        2. Відправляємо GET /api/feedback
        3. Перевіяємо що повертається список з нашими відгуками
        
        ЧОМУ ТАК:
        - На головній сторінці показуємо останні відгуки
        - Треба перевірити що вони правильно повертаються
        """
        # Створюємо 2 відгука
        with app_with_db.app_context():
            for i in range(2):
                fb = Feedback(
                    name=f'User {i}',
                    email=f'user{i}@example.com',
                    message=f'Message {i}',
                    rating=i+1
                )
                db.session.add(fb)
            db.session.commit()
        
        # Отримуємо список
        response = client.get('/api/feedback')
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]['name'] == 'User 1'  # Новіші першими
        assert data[1]['name'] == 'User 0'
    
    def test_delete_feedback_as_admin(self, client, logged_in_admin_client_db, app_with_db):
        """
        ТЕСТ 7: Адмін може видалити відгук.
        
        ЩО РОБИМО:
        1. Маємо залогованого адміна (logged_in_admin_client)
        2. Створюємо відгук
        3. Відправляємо DELETE запит
        4. Перевіяємо що повертається 200
        5. Перевіяємо що відгук видален з БД
        
        ЧОМУ ТАК:
        - Адмін повинен модерувати відгуки (видаляти спам, образи)
        - Тільки адмін має право видаляти
        """
        # Створюємо відгук
        with app_with_db.app_context():
            fb = Feedback(
                name='Spam User',
                email='spam@example.com',
                message='Bad feedback',
                rating=1
            )
            db.session.add(fb)
            db.session.commit()
            fb_id = fb.id
        
        # Адмін видаляє
        response = logged_in_admin_client_db.delete(f'/api/feedback/{fb_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # Перевіяємо що видален
        with app_with_db.app_context():
            feedback = Feedback.query.get(fb_id)
            assert feedback is None
    
    def test_delete_feedback_without_admin(self, client, logged_in_client_db, app_with_db):
        """
        ТЕСТ 8: Звичайний користувач НЕ може видалити відгук.
        
        ЩО РОБИМО:
        1. Маємо звичайного користувача (logged_in_client)
        2. Намагаємось видалити відгук
        3. Перевіяємо що повертається 403 (доступ заборонено)
        4. Відгук залишається в БД
        
        ЧОМУ ТАК:
        - Безпека: тільки адмін має доступ до адмін-операцій
        """
        # Створюємо відгук
        with app_with_db.app_context():
            fb = Feedback(
                name='Normal User',
                email='normal@example.com',
                message='Normal feedback',
                rating=3
            )
            db.session.add(fb)
            db.session.commit()
            fb_id = fb.id
        
        # Звичайний користувач намагається видалити
        response = logged_in_client_db.delete(f'/api/feedback/{fb_id}')
        
        # Повинен бути 403 (доступ заборонено)
        assert response.status_code == 403
        data = response.get_json()
        assert data['status'] == 'error'
        
        # Перевіяємо що відгук НЕ видален
        with app_with_db.app_context():
            feedback = Feedback.query.get(fb_id)
            assert feedback is not None


class TestHealthAPI:
    """Integration тести для health endpoint."""
    
    def test_health_endpoint(self, client):
        """
        ТЕСТ 9: Health endpoint для Docker healthcheck.
        
        ЩО РОБИМО:
        1. Відправляємо GET /health
        2. Перевіяємо що повертається 200
        3. Перевіяємо що статус 'ok'
        
        ЧОМУ ТАК:
        - Docker використовує цей endpoint щоб перевірити живий ли контейнер
        - Якщо /health падає → контейнер перезапускається
        """
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
