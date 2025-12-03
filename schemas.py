"""
Marshmallow схеми для валідації API запитів та серіалізації відповідей
"""
from flask_marshmallow import Marshmallow
from marshmallow import fields, validates, validates_schema, ValidationError, validate
import re

ma = Marshmallow()

# ===== Product Schemas =====
class ProductSchema(ma.Schema):
    """Схема для Product моделі"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(validate=validate.Length(max=1000))
    price = fields.Float(required=True, validate=validate.Range(min=0))
    type = fields.Str(
        required=True,
        validate=validate.OneOf([
            'subscription',
            'quote_pack',
            'theme',
            'journal_template',
            'habit_course'
        ])
    )
    slug = fields.Str(dump_only=True)
    is_active = fields.Bool()
    created_at = fields.DateTime(dump_only=True)

    class Meta:
        ordered = True


# ===== Order Schemas =====
class OrderItemInputSchema(ma.Schema):
    """Схема для вхідних даних item в замовленні"""
    product_id = fields.Int(required=True, validate=validate.Range(min=1))
    quantity = fields.Int(required=True, validate=validate.Range(min=1, max=100))

    class Meta:
        ordered = True


class OrderItemOutputSchema(ma.Schema):
    """Схема для вихідних даних item в замовленні"""
    id = fields.Int(dump_only=True)
    product_id = fields.Int()
    product_name = fields.Str()
    quantity = fields.Int()
    unit_price = fields.Float()
    subtotal = fields.Float()

    class Meta:
        ordered = True


class CreateOrderSchema(ma.Schema):
    """Схема для створення замовлення"""
    items = fields.List(fields.Nested(OrderItemInputSchema), required=True, validate=validate.Length(min=1))

    class Meta:
        ordered = True


class OrderOutputSchema(ma.Schema):
    """Схема для відповіді з замовленням"""
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    status = fields.Str()
    total_amount = fields.Float()
    items = fields.List(fields.Nested(OrderItemOutputSchema))
    created_at = fields.DateTime(dump_only=True)

    class Meta:
        ordered = True


# ===== Payment Schemas =====
class CreatePaymentSchema(ma.Schema):
    """Схема для створення платежу"""
    order_id = fields.Int(required=True, validate=validate.Range(min=1))
    payment_method = fields.Str(
        required=True,
        validate=validate.OneOf(['card', 'online_banking', 'paypal'])
    )
    
    # Поля для картки (обов'язкові тільки якщо payment_method == 'card')
    card_number = fields.Str(validate=validate.Length(min=13, max=19))
    card_holder = fields.Str(validate=validate.Length(min=1, max=200))
    card_expiry = fields.Str(validate=validate.Regexp(r'^\d{2}/\d{2}$', error='Формат: MM/YY'))
    card_cvv = fields.Str(validate=validate.Regexp(r'^\d{3,4}$', error='CVV повинен бути 3-4 цифри'))

    @validates('card_number')
    def validate_card_number(self, value):
        """Валідація номера картки (тільки цифри)"""
        if value and not re.match(r'^\d{13,19}$', value):
            raise ValidationError('Номер картки повинен містити 13-19 цифр')

    @validates_schema
    def validate_card_fields(self, data, **kwargs):
        """Переконуємось, що для картки передано всі обов'язкові поля."""
        if data.get('payment_method') == 'card':
            missing = []
            for field in ['card_number', 'card_holder', 'card_expiry', 'card_cvv']:
                if not data.get(field):
                    missing.append(field)
            if missing:
                raise ValidationError({field: 'Поле обов\'язкове для оплати карткою' for field in missing})
        else:
            # Якщо інший метод оплати, забороняємо передавати дані картки
            unexpected = [
                field for field in ['card_number', 'card_holder', 'card_expiry', 'card_cvv']
                if data.get(field)
            ]
            if unexpected:
                raise ValidationError({field: 'Поле дозволено тільки для payment_method=card' for field in unexpected})

    class Meta:
        ordered = True


class PaymentOutputSchema(ma.Schema):
    """Схема для відповіді з платежем"""
    id = fields.Int(dump_only=True)
    order_id = fields.Int()
    payment_method = fields.Str()
    amount = fields.Float()
    status = fields.Str()
    transaction_id = fields.Str()
    card_last4 = fields.Str()
    card_brand = fields.Str()
    completed_at = fields.DateTime()

    class Meta:
        ordered = True


# ===== Feedback Schemas =====
class CreateFeedbackSchema(ma.Schema):
    """Схема для створення відгуку"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True, validate=validate.Length(max=200))
    message = fields.Str(required=True, validate=validate.Length(min=1, max=2000))
    rating = fields.Int(validate=validate.Range(min=1, max=5))

    class Meta:
        ordered = True


class FeedbackOutputSchema(ma.Schema):
    """Схема для відповіді з відгуком"""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    email = fields.Str()
    message = fields.Str()
    rating = fields.Int()
    created_at = fields.DateTime(dump_only=True)

    class Meta:
        ordered = True


# ===== Journal Schemas =====
class CreateJournalEntrySchema(ma.Schema):
    """Схема для створення запису настрою"""
    mood = fields.Str(
        required=True,
        validate=validate.OneOf(['happy', 'neutral', 'sad'])
    )
    date = fields.Date(required=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    content = fields.Str(validate=validate.Length(max=5000))
    activities = fields.List(fields.Str())

    class Meta:
        ordered = True


class JournalEntryOutputSchema(ma.Schema):
    """Схема для відповіді з записом настрою"""
    id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    mood = fields.Str()
    mood_emoji = fields.Str()
    date = fields.Date()
    title = fields.Str()
    content = fields.Str()
    activities = fields.List(fields.Str())
    created_at = fields.DateTime(dump_only=True)

    class Meta:
        ordered = True


# ===== Auth Schemas =====
class LoginSchema(ma.Schema):
    """Схема для логіну"""
    email = fields.Email(required=True, validate=validate.Length(max=200))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=200))

    class Meta:
        ordered = True


class RegisterSchema(ma.Schema):
    """Схема для реєстрації"""
    email = fields.Email(required=True, validate=validate.Length(max=200))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=200))

    class Meta:
        ordered = True


class UserOutputSchema(ma.Schema):
    """Схема для відповіді з користувачем"""
    id = fields.Int(dump_only=True)
    email = fields.Str()
    is_premium = fields.Bool()

    class Meta:
        ordered = True


# ===== Ініціалізація схем =====
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

create_order_schema = CreateOrderSchema()
order_output_schema = OrderOutputSchema()

create_payment_schema = CreatePaymentSchema()
payment_output_schema = PaymentOutputSchema()

create_feedback_schema = CreateFeedbackSchema()
feedback_output_schema = FeedbackOutputSchema()
feedbacks_schema = FeedbackOutputSchema(many=True)

create_journal_entry_schema = CreateJournalEntrySchema()
journal_entry_output_schema = JournalEntryOutputSchema()

login_schema = LoginSchema()
register_schema = RegisterSchema()
user_output_schema = UserOutputSchema()
