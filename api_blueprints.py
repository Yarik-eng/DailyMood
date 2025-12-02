"""
API Blueprints для версіювання
v1 - базова версія API (backwards compatibility)
v2 - покращена версія з валідацією та розширеною обробкою помилок
"""
from flask import Blueprint, jsonify, request, session
from functools import wraps
from flasgger import swag_from
from models import db, Product, Order, OrderItem, Payment, Feedback, MoodEntry, User
from schemas import (
    products_schema, create_order_schema, order_output_schema,
    create_payment_schema, payment_output_schema, create_feedback_schema,
    feedback_output_schema, feedbacks_schema, create_journal_entry_schema,
    journal_entry_output_schema
)
from marshmallow import ValidationError
import logging
from datetime import datetime
import uuid

# ===== Blueprints =====
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')


# ===== Helper functions =====
def validate_request_data(schema, data=None):
    """Валідує вхідні дані за допомогою Marshmallow схеми"""
    if data is None:
        data = request.get_json()
    
    if not data:
        return None, (jsonify({'status': 'error', 'message': 'Відсутні дані в запиті'}), 400)
    
    try:
        validated_data = schema.load(data)
        return validated_data, None
    except ValidationError as err:
        return None, (jsonify({
            'status': 'error',
            'message': 'Помилка валідації',
            'errors': err.messages
        }), 400)


def login_required_api(f):
    """Декоратор для API endpoints що потребують авторизації"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Потрібна авторизація'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ==================== API V1 (Базова версія без валідації) ====================
# Ці endpoints підтримують backwards compatibility

@api_v1.route('/products', methods=['GET'])
def v1_get_products():
    """V1: Отримати список продуктів"""
    try:
        products = Product.query.filter_by(is_active=True).all()
        return jsonify([p.to_dict() for p in products]), 200
    except Exception as e:
        logging.error(f"V1 Error getting products: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_v1.route('/orders', methods=['POST'])
@login_required_api
def v1_create_order():
    """V1: Створити замовлення (без валідації)"""
    try:
        data = request.get_json(silent=True) or {}
        items_data = data.get('items', [])
        
        if not items_data:
            return jsonify({'status': 'error', 'message': 'Замовлення повинно містити товари'}), 400
        
        user_id = session['user_id']
        order = Order(user_id=user_id, status='new')
        db.session.add(order)
        db.session.flush()
        
        for item_data in items_data:
            product_id = item_data.get('product_id')
            quantity = item_data.get('quantity', 1)
            
            product = Product.query.get(product_id)
            if not product or not product.is_active:
                db.session.rollback()
                return jsonify({'status': 'error', 'message': f'Продукт #{product_id} недоступний'}), 400
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
                subtotal=product.price * quantity
            )
            db.session.add(order_item)
        
        order.calculate_total()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Замовлення створено',
            'order': order.to_dict(include_items=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"V1 Error creating order: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@api_v1.route('/feedback', methods=['POST'])
def v1_create_feedback():
    """V1: Створити відгук (без валідації email)"""
    try:
        data = request.get_json(silent=True) or {}
        msg = (data.get('message') or '').strip()
        
        if not msg:
            return jsonify({'status': 'error', 'message': 'Missing message'}), 400
        
        fb = Feedback(
            name=(data.get('name') or '').strip() or None,
            email=(data.get('email') or '').strip() or None,
            message=msg,
            rating=data.get('rating')
        )
        db.session.add(fb)
        db.session.commit()
        return jsonify({'status': 'success', 'data': fb.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"V1 Error creating feedback: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== API V2 (Покращена версія з валідацією) ====================

@api_v2.route('/products', methods=['GET'])
def v2_get_products():
    """V2: Отримати список продуктів з серіалізацією"""
    try:
        products = Product.query.filter_by(is_active=True).all()
        # Використовуємо to_dict() замість Marshmallow для простоти
        products_data = [p.to_dict() for p in products]
        return jsonify({
            'status': 'success',
            'count': len(products_data),
            'data': products_data
        }), 200
    except Exception as e:
        logging.error(f"V2 Error getting products: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Не вдалося отримати список продуктів',
            'code': 'PRODUCTS_FETCH_ERROR'
        }), 500


@api_v2.route('/orders', methods=['POST'])
@login_required_api
def v2_create_order():
    """V2: Створити замовлення з валідацією"""
    try:
        # Валідація вхідних даних
        validated_data, error = validate_request_data(create_order_schema)
        if error:
            return error
        
        items_data = validated_data['items']
        user_id = session['user_id']
        
        order = Order(user_id=user_id, status='new')
        db.session.add(order)
        db.session.flush()
        
        for item_data in items_data:
            product_id = item_data['product_id']
            quantity = item_data['quantity']
            
            product = Product.query.get(product_id)
            if not product or not product.is_active:
                db.session.rollback()
                return jsonify({
                    'status': 'error',
                    'message': f'Продукт #{product_id} недоступний',
                    'code': 'PRODUCT_NOT_FOUND'
                }), 404
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
                subtotal=product.price * quantity
            )
            db.session.add(order_item)
        
        order.calculate_total()
        db.session.commit()
        
        # Серіалізація відповіді
        order_data = order_output_schema.dump(order.to_dict(include_items=True))
        
        return jsonify({
            'status': 'success',
            'message': 'Замовлення створено',
            'data': order_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"V2 Error creating order: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Не вдалося створити замовлення',
            'code': 'ORDER_CREATE_ERROR'
        }), 500


@api_v2.route('/payments', methods=['POST'])
@login_required_api
def v2_create_payment():
    """V2: Створити платіж з валідацією"""
    try:
        # Валідація вхідних даних
        validated_data, error = validate_request_data(create_payment_schema)
        if error:
            return error
        
        order_id = validated_data['order_id']
        payment_method = validated_data['payment_method']
        
        # Додаткова валідація для картки
        if payment_method == 'card':
            required_card_fields = ['card_number', 'card_holder', 'card_expiry', 'card_cvv']
            missing_fields = [f for f in required_card_fields if f not in validated_data or not validated_data[f]]
            if missing_fields:
                return jsonify({
                    'status': 'error',
                    'message': f'Для оплати карткою обов\'язкові поля: {", ".join(missing_fields)}',
                    'code': 'MISSING_CARD_FIELDS'
                }), 400
        
        # Перевірка замовлення
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'status': 'error',
                'message': 'Замовлення не знайдено',
                'code': 'ORDER_NOT_FOUND'
            }), 404
        
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # Перевірка чи вже є оплата
        if order.payment:
            return jsonify({
                'status': 'error',
                'message': 'Замовлення вже має платіж',
                'code': 'PAYMENT_EXISTS'
            }), 400
        
        # Створення платежу
        payment = Payment(
            order_id=order.id,
            payment_method=payment_method,
            amount=order.total_amount,
            status='pending'
        )
        
        # Обробка деталей карти
        if payment_method == 'card':
            card_number = validated_data['card_number'].replace(' ', '').strip()
            if len(card_number) >= 4:
                payment.card_last4 = card_number[-4:]
            payment.card_brand = validated_data.get('card_brand', 'Unknown')
        
        # Симуляція обробки платежу
        prefix = {'card': 'TXN', 'online_banking': 'BANK', 'paypal': 'PP'}.get(payment_method, 'TXN')
        payment.transaction_id = f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
        payment.status = 'completed'
        payment.completed_at = datetime.utcnow()
        
        # Для цифрових продуктів (Premium) - одразу completed
        is_digital = any('premium' in (item.product.name or '').lower() or 
                       'преміум' in (item.product.name or '').lower() 
                       for item in order.items)
        order.status = 'completed' if is_digital else 'processing'
        
        # Активація Premium для користувача
        if is_digital and user:
            user.is_premium = True
            logging.info(f"Premium активовано для користувача {user.email}")
        
        db.session.add(payment)
        db.session.commit()
        
        # Серіалізація відповіді
        payment_data = payment_output_schema.dump(payment.to_dict())
        
        return jsonify({
            'status': 'success',
            'message': 'Платіж створено успішно',
            'data': {
                'payment': payment_data,
                'order': order.to_dict()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"V2 Error creating payment: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Не вдалося створити платіж',
            'code': 'PAYMENT_CREATE_ERROR'
        }), 500


@api_v2.route('/feedback', methods=['POST'])
def v2_create_feedback():
    """V2: Створити відгук з валідацією"""
    try:
        # Валідація вхідних даних
        validated_data, error = validate_request_data(create_feedback_schema)
        if error:
            return error
        
        fb = Feedback(
            name=validated_data['name'],
            email=validated_data['email'],
            message=validated_data['message'],
            rating=validated_data.get('rating')
        )
        db.session.add(fb)
        db.session.commit()
        
        # Серіалізація відповіді
        feedback_data = feedback_output_schema.dump(fb.to_dict())
        
        return jsonify({
            'status': 'success',
            'message': 'Відгук успішно створено',
            'data': feedback_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"V2 Error creating feedback: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Не вдалося створити відгук',
            'code': 'FEEDBACK_CREATE_ERROR'
        }), 500


@api_v2.route('/feedback', methods=['GET'])
def v2_list_feedback():
    """V2: Список відгуків"""
    try:
        feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).limit(50).all()
        result = feedbacks_schema.dump([f.to_dict() for f in feedbacks])
        
        return jsonify({
            'status': 'success',
            'count': len(result),
            'data': result
        }), 200
        
    except Exception as e:
        logging.error(f"V2 Error listing feedback: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Не вдалося отримати відгуки',
            'code': 'FEEDBACK_FETCH_ERROR'
        }), 500


@api_v2.route('/journal', methods=['POST'])
@login_required_api
def v2_add_journal_entry():
    """V2: Створити запис настрою з валідацією"""
    try:
        user_id = session['user_id']
        
        # Валідація вхідних даних
        validated_data, error = validate_request_data(create_journal_entry_schema)
        if error:
            return error
        
        # Обробка activities
        activities_input = validated_data.get('activities', '')
        if isinstance(activities_input, str) and activities_input:
            activities_list = [a.strip() for a in activities_input.split(',') if a.strip()]
            activities = ','.join(activities_list)
        else:
            activities = None
        
        entry = MoodEntry(
            mood=validated_data['mood'],
            date=validated_data['date'],
            title=validated_data['title'],
            user_id=user_id,
            content=validated_data.get('content'),
            activities=activities
        )
        
        db.session.add(entry)
        db.session.commit()
        
        # Серіалізація відповіді
        entry_data = journal_entry_output_schema.dump(entry.to_dict())
        
        return jsonify({
            'status': 'success',
            'message': 'Запис успішно збережено',
            'data': entry_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"V2 Error adding journal entry: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Не вдалося створити запис',
            'code': 'JOURNAL_CREATE_ERROR'
        }), 500
