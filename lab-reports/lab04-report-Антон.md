# Звіт з лабораторної роботи 4

## Реалізація бази даних для вебпроєкту DailyMood 3.0

### Інформація про команду
- Назва команди: Ctrl+V
- Автор звіту: Приступа Антон
- Роль: Тестувальник (мануальне тестування інтерфейсу)

#### Склад команди
- Ярослав Мерчук — лідер, full‑stack розробник
- Мирон Настя — документатор (звіти lab04, README.md)
- Кутецька Аліна — UI/UX (консультації, ідеї)
- Приступа Антон — тестувальник (цей звіт)

## Завдання

### Обрана предметна область
DailyMood — застосунок для відстеження настрою з журналом, статистикою, звичками/цілями та магазином цифрових wellness‑ресурсів. Є Premium‑можливості (Mood Predictor, Activity Recommendations), темізація профілю, аватари, адмін‑панелі.

### Реалізовані вимоги
- [x] Рівень 1: Створено БД (SQLite у dev), CRUD‑операції, адмін‑панель відгуків, магазин (продукти/замовлення)
- [x] Рівень 2: Додаткові таблиці (Payment, OrderItem, MoodEntry з user_id, Habit, HabitCompletion, MonthlyGoal)
- [x] Рівень 3: Activity Recommendations та Mood Predictor (+ експорт журналу, статистика)

## Хід виконання роботи

### Підготовка середовища розробки
- Python 3.9+
- Flask 2.x, Flask‑SQLAlchemy 3.x

Кроки розгортання (локально):
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_products.py
python app.py
```

### Структура проєкту
```
DailyMood3.0/
├── app.py               
├── models.py             
├── requirements.txt     
├── run.bat               
├── ARCHITECTURE.md        
├── scripts/
│   ├── init_db.py         
│   └── seed_products.py 
├── templates/
│   ├── base.html       
│   ├── index.html       
│   ├── register.html      
│   ├── login.html       
│   ├── store.html         
│   ├── journal.html      
│   ├── statistics.html   
│   ├── goals.html         
│   ├── about.html         
│   └── favorites.html    
├── static/
│   ├── style.css          
│   ├── script.js          
│   ├── css/
│   │   ├── goals.css
│   │   └── transitions.css
│   ├── js/
│   │   └── i18n.js        
│   └── translations/
│       ├── en.js
│       ├── uk.js
│       └── quotes.js
└── lab-reports/
```

#### Опис ключових файлів
- **app.py** — головний файл застосунку, містить Flask-маршрути, бізнес-логіку, API ендпоїнти, систему автентифікації та адмін-панелі
- **models.py** — моделі бази даних (User, Product, Order, OrderItem, Payment, MoodEntry, Feedback, Habit, HabitCompletion, MonthlyGoal)
- **requirements.txt** — список залежностей Python (пакети Flask, SQLAlchemy, тощо)
- **scripts/init_db.py** — скрипт ініціалізації БД, створює таблиці та адмін-користувача
- **scripts/seed_products.py** — заповнює БД тестовими продуктами магазину
- **templates/** — HTML-шаблони Jinja2 (сторінки журналу, магазину, статистики, адмін-панелі)
- **static/style.css** — глобальні стилі (темізація, адаптивність, анімації)
- **static/script.js** — клієнтська логіка (взаємодія з API, динамічні форми, теми, валідація)
- **static/js/i18n.js** — система міжнароднізації (перемикання української/англійської)
- **static/translations/** — файли перекладів та цитат для UI

### Проектування бази даних                   
```

### Проектування бази даних
База даних спроектована для зберігання інформації про користувачів, їхні записи настрою, продукти магазину, замовлення, платежі, відгуки, звички та цілі. Використовуємо реляційну модель з нормалізованими таблицями та чіткими зв'язками між сутностями.

#### Схема бази даних
Основні таблиці (SQLAlchemy → SQLite у dev):
- users(id, email, password_hash, is_admin, is_premium, premium_started_at, premium_expires_at, created_at, avatar)
- products(id, name, slug, type, description, price, is_active, created_at)
- orders(id, user_id, status, total_amount, created_at, updated_at)
- order_items(id, order_id, product_id, quantity, unit_price, subtotal)
- payments(id, order_id[unique], payment_method, status, amount, transaction_id, card_last4, card_brand, payment_details, created_at, completed_at)
- mood_entries(id, user_id, mood, date, title, content, activities, created_at)
- feedback(id, name, email, message, rating, created_at)
- habits(id, name, type, created_at)
- habit_completions(id, habit_id, date)
- monthly_goals(id, name, deadline, completed, created_at)

Особливості:
- Прив'язка `MoodEntry.user_id` (видимість лише власнику)
- Order ↔ Payment — 1:1; User → Order — 1:N; Order → OrderItem — 1:N


### Опис реалізованої функціональності

#### Система відгуків
- API: `POST /api/feedback`, `GET /api/feedback`, `DELETE /api/feedback/<id>` (admin)
- Адмін‑панель: перегляд/видалення відгуків

#### Магазин
- Каталог: `GET /api/products` (активні для всіх; усі — для адміна)
- Замовлення: `POST /api/orders` (масив товарів)
- Оплата: `POST /api/payments` (card/online_banking/paypal), `transaction_id`, статуси

#### Адміністративна панель
- Керування користувачами, продуктами, замовленнями, відгуками

#### Додатково (Premium/аналітика)
- Рекомендації активностей, прогноз настрою
- Журнал: експорт CSV/JSON, фільтри, власність записів
- Статистика за періоди

## Ключові фрагменти коду

### Ініціалізація бази даних (SQLAlchemy)
```python
from models import db
from app import app

with app.app_context():
	db.create_all()  # створює таблиці, якщо відсутні
```

### Моделі (приклад)
```python
class Feedback(db.Model):
	__tablename__ = 'feedback'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(120))
	email = db.Column(db.String(255))
	message = db.Column(db.Text, nullable=False)
	rating = db.Column(db.Integer)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
```

### CRUD операції (приклади)
```python
# Create (відгук)
@app.route('/api/feedback', methods=['POST'])
def create_feedback():
	data = request.get_json(silent=True) or {}
	fb = Feedback(name=data.get('name'), email=data.get('email'),
				  message=data.get('message'), rating=data.get('rating'))
	db.session.add(fb); db.session.commit()
	return jsonify({'status':'success','data': fb.to_dict()}), 201

# Read (перелік відгуків)
@app.route('/api/feedback', methods=['GET'])
def list_feedback():
	q = Feedback.query.order_by(Feedback.created_at.desc()).limit(50).all()
	return jsonify([f.to_dict() for f in q])

# Update (статус замовлення — адмін)
@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@admin_required
def update_order_status(order_id):
	order = Order.query.get_or_404(order_id)
	order.status = (request.get_json(silent=True) or {}).get('status','new')
	db.session.commit(); return jsonify({'status':'success'})

# Delete (видалення відгуку — адмін)
@app.route('/api/feedback/<int:feedback_id>', methods=['DELETE'])
@admin_required
def delete_feedback(feedback_id):
	fb = Feedback.query.get_or_404(feedback_id)
	db.session.delete(fb); db.session.commit()
	return jsonify({'status':'success'})
```

### Маршрути (приклади)
```python
@app.route('/api/orders', methods=['POST'])
@login_required
def create_order(): ...

@app.route('/api/payments', methods=['POST'])
@login_required
def create_payment(): ...
```

### JOIN / зв'язки (Order ↔ Items ↔ Product)
```python
# SQLAlchemy віддає пов'язані записи через зв'язки моделі
order = Order.query.get(order_id)
items = [
	{
		'product': it.product.name,
		'qty': it.quantity,
		'subtotal': it.subtotal
	}
	for it in order.items
]
# Або явно через join
from sqlalchemy import select
rows = db.session.execute(
	select(Order, OrderItem, Product)
	.join(OrderItem, OrderItem.order_id==Order.id)
	.join(Product, Product.id==OrderItem.product_id)
	.where(Order.id==order_id)
).all()
```

## Розподіл обов'язків
- Ярослав: повна реалізація бекенду/фронтенду/БД
- Настя: звіти lab04, README.md
- Аліна: консультації по дизайну, пропозиції UI‑покращень
- Антон: тестування інтерфейсу (цей звіт)

## Скріншоти
- Додати під час захисту (форми, оплата, адмін‑панель, статистика)

## Тестування
1. Додавання відгуку та перегляд у адмін‑панелі
2. Створення замовлення і проведення «оплати» в демо‑режимі
3. CRUD продуктів (адмін), зміна статусів замовлень
4. Перевірка приватності журналу (видимість лише своїх записів)
5. Експорт журналу у CSV/JSON

## Висновки
- Інтерфейс працює стабільно у основних сценаріях; критичних збоїв не виявлено

Очікувана оцінка: **10-11 балів**

