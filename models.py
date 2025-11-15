from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(db.Model):
    """Модель користувача для реєстрації, входу та прив'язки замовлень."""
    
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    premium_started_at = db.Column(db.DateTime, nullable=True)
    premium_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    avatar = db.Column(db.String(255), nullable=True)
    
    # Зв'язок з замовленнями (один користувач - багато замовлень)
    orders = db.relationship('Order', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Встановлює хеш пароля."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Перевіряє пароль проти збереженого хешу."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Повертає дані користувача без пароля."""
        return {
            'id': self.id,
            'email': self.email,
            'is_admin': self.is_admin,
            'is_premium': self.is_premium,
            'premium_started_at': self.premium_started_at.isoformat() if self.premium_started_at else None,
            'premium_expires_at': self.premium_expires_at.isoformat() if self.premium_expires_at else None,
            'created_at': self.created_at.isoformat(),
            'avatar': self.avatar
        }


class Product(db.Model):
    """Модель продукту для магазину wellness-ресурсів (пакети цитат, теми, шаблони)."""
    
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # quote_pack, theme, journal_template, habit_course
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False, default=0.0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Зв'язок з елементами замовлень
    order_items = db.relationship('OrderItem', backref='product', lazy='dynamic')
    
    def to_dict(self):
        """Повертає продукт у вигляді словника."""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'type': self.type,
            'description': self.description,
            'price': self.price,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }


class Order(db.Model):
    """Модель замовлення користувача."""
    
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='new')  # new, processing, completed, canceled
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Зв'язок з елементами замовлення
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    
    def calculate_total(self):
        """Розраховує загальну суму замовлення з його елементів."""
        total = sum(item.subtotal for item in self.items)
        self.total_amount = total
        return total
    
    def to_dict(self, include_items=False):
        """Повертає замовлення у вигляді словника."""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user.email if self.user else None,
            'status': self.status,
            'total_amount': self.total_amount,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        if include_items:
            result['items'] = [item.to_dict() for item in self.items]
        return result


class OrderItem(db.Model):
    """Модель елемента замовлення (зв'язок замовлення з продуктами)."""
    
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)  # Ціна на момент покупки
    subtotal = db.Column(db.Float, nullable=False)
    
    def to_dict(self):
        """Повертає елемент замовлення у вигляді словника."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'subtotal': self.subtotal
        }


class MoodEntry(db.Model):
    """Модель для зберігання записів настрою."""
    
    VALID_MOODS = ['happy', 'neutral', 'sad']
    
    __tablename__ = 'mood_entries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mood = db.Column(db.String(32), nullable=False)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    activities = db.Column(db.String(500), nullable=True)  # Зберігаємо як comma-separated string
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Зв'язок з користувачем
    user = db.relationship('User', backref=db.backref('mood_entries', lazy='dynamic', cascade='all, delete-orphan'))

    def __init__(self, mood, date, title, user_id, content=None, activities=None):
        if mood not in self.VALID_MOODS:
            raise ValueError(f'Недійсне значення настрою. Допустимі значення: {", ".join(self.VALID_MOODS)}')
        self.mood = mood
        self.date = date
        self.title = title
        self.user_id = user_id
        self.content = content
        self.activities = activities

    def to_dict(self):
        """Конвертує запис в словник для JSON відповіді."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'mood': self.mood,
            'date': self.date.isoformat(),
            'title': self.title,
            'content': self.content,
            'activities': self.activities.split(',') if self.activities else [],
            'created_at': self.created_at.isoformat(),
            'mood_emoji': self.get_mood_emoji()
        }
    
    def get_mood_emoji(self):
        """Повертає емодзі для відповідного настрою."""
        emoji_map = {
            'happy': '😊',
            'neutral': '😐',
            'sad': '😢'
        }
        return emoji_map.get(self.mood, '❓')


class Feedback(db.Model):
    """Модель для зберігання відгуків користувачів."""

    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Повертає відгук у вигляді словника для JSON відповіді."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'message': self.message,
            'rating': self.rating,
            'created_at': self.created_at.isoformat()
        }


class Payment(db.Model):
    """Модель для зберігання інформації про оплату замовлень."""

    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)
    payment_method = db.Column(db.String(50), nullable=False)  # card, cash, online_banking
    status = db.Column(db.String(50), nullable=False, default='pending')  # pending, completed, failed, refunded
    amount = db.Column(db.Float, nullable=False)
    transaction_id = db.Column(db.String(255), nullable=True)  # ID транзакції від платіжної системи
    
    # Дані карти (зберігаємо тільки останні 4 цифри для безпеки)
    card_last4 = db.Column(db.String(4), nullable=True)
    card_brand = db.Column(db.String(20), nullable=True)  # Visa, Mastercard, etc.
    
    # Дані для готівки/банкінгу
    payment_details = db.Column(db.Text, nullable=True)  # JSON з додатковими деталями
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Зв'язок з замовленням
    order = db.relationship('Order', backref=db.backref('payment', uselist=False, cascade='all, delete-orphan'))

    def to_dict(self):
        """Повертає платіж у вигляді словника."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'payment_method': self.payment_method,
            'status': self.status,
            'amount': self.amount,
            'transaction_id': self.transaction_id,
            'card_last4': self.card_last4,
            'card_brand': self.card_brand,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }