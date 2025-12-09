"""
Unit тести для моделей - тестуємо функції окремо без залежностей.

Unit тест = тест однієї функції/методу окремо.
Не тестуємо цілий ланцюг, лише окремі шматки коду.
"""

import pytest
from models import User, Feedback
from app import db


class TestUserModel:
    """Група тестів для моделі User (клас користувача)."""
    
    def test_set_password_hashes_password(self, app_with_db):
        """
        ТЕСТ 1: Перевірка хешування пароля.
        
        ЩО РОБИМО:
        - Створюємо користувача
        - Встановлюємо пароль через set_password()
        - Перевіяємо що пароль не зберігається в плайні, а хешується
        
        ЧОМУ ТАК:
        - Це базова безпека! Пароль ніколи не повинен зберігатися просто так.
        - Мусить зберігатися лише хеш (одностороння функція).
        """
        with app_with_db.app_context():
            user = User(email='test@example.com')
            user.set_password('my_secret_password')
            
            # Перевіяємо що хеш не дорівнює оригіналу
            assert user.password_hash != 'my_secret_password'
            assert user.password_hash is not None
            assert len(user.password_hash) > 20  # Хеш завжди довгий
    
    def test_check_password_correct(self, app_with_db, test_user):
        """
        ТЕСТ 2: Перевірка що правильний пароль повертає True.
        
        ЩО РОБИМО:
        - Маємо test_user з паролем 'password123' (з conftest.py)
        - Перевіяємо його через check_password()
        - Результат має бути True
        
        ЧОМУ ТАК:
        - Коли користувач логінить, ми перевіряємо пароль через цей метод.
        - Якщо пароль правильний -> повертаємо True -> дозволяємо вхід.
        """
        with app_with_db.app_context():
            result = test_user.check_password('password123')
            assert result == True
    
    def test_check_password_incorrect(self, app_with_db, test_user):
        """
        ТЕСТ 3: Перевірка що неправильний пароль повертає False.
        
        ЩО РОБИМО:
        - Маємо test_user з паролем 'password123'
        - Перевіяємо його з НЕПРАВИЛЬНИМ паролем 'wrongpassword'
        - Результат має бути False
        
        ЧОМУ ТАК:
        - Це протилежний сценарій: користувач вводить неправильний пароль.
        - Система повинна відхилити такий попит.
        """
        with app_with_db.app_context():
            result = test_user.check_password('wrongpassword')
            assert result == False
    
    def test_user_to_dict_no_password(self, app_with_db, test_user):
        """
        ТЕСТ 4: Перевірка що to_dict() не повертає пароль.
        
        ЩО РОБИМО:
        - Викликаємо test_user.to_dict()
        - Перевіяємо що в результаті немає поля 'password_hash'
        - Перевіяємо що є інші поля (email, id, и т.д.)
        
        ЧОМУ ТАК:
        - Коли відправляємо дані клієнту (браузер), НЕ МОЖЕМО відправляти пароль!
        - to_dict() конвертує модель в JSON - це використовується для відповідей API.
        - Безпека: ніколи не відправляй чутливі дані клієнту.
        """
        with app_with_db.app_context():
            user_dict = test_user.to_dict()
            
            # Перевіяємо що пароль НЕ в словнику
            assert 'password_hash' not in user_dict
            assert 'password' not in user_dict
            
            # Перевіяємо що важливі поля ЕСТЬ
            assert 'id' in user_dict
            assert 'email' in user_dict
            assert user_dict['email'] == 'user@test.com'


class TestFeedbackModel:
    """Група тестів для моделі Feedback (відгуки користувачів)."""
    
    def test_feedback_to_dict(self, app_with_db):
        """
        ТЕСТ 5: Перевірка конвертації відгука в словник.
        
        ЩО РОБИМО:
        - Створюємо відгук з назвою, email, повідомленням, рейтингом
        - Викликаємо to_dict()
        - Перевіяємо що всі поля присутні в результаті
        
        ЧОМУ ТАК:
        - Коли клієнт створює відгук, ми його зберігаємо в БД.
        - Потім повертаємо його у вигляді JSON через to_dict().
        - Треба переконатися що нічого не загубилось.
        """
        with app_with_db.app_context():
            feedback = Feedback(
                name='John Doe',
                email='john@example.com',
                message='Great app!',
                rating=5
            )
            db.session.add(feedback)
            db.session.commit()
            
            # Конвертуємо в словник
            feedback_dict = feedback.to_dict()
            
            # Перевіяємо всі важливі поля
            assert feedback_dict['name'] == 'John Doe'
            assert feedback_dict['email'] == 'john@example.com'
            assert feedback_dict['message'] == 'Great app!'
            assert feedback_dict['rating'] == 5
            assert 'created_at' in feedback_dict
