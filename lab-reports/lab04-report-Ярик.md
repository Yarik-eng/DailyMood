# Звіт з лабораторної роботи 4

## Реалізація бази даних для вебпроєкту DailyMood 3.0

### Інформація про команду
- Назва команди: Ctrl+V
- Автор звіту: Ярослав Мерчук
- Роль: Лідер команди, Full‑stack розробник (виконав увесь код і БД самостійно)

#### Склад команди
- Ярослав Мерчук — лідер, full‑stack розробник
- Мирон Настя — документатор (підготовка звітів, написання README.md)
- Кутецька Аліна — UI/UX (консультації по дизайну, ідеї покращення UI)
- Приступа Антон — тестувальник (перевірка інтерфейсу, кліки по кнопках/формах)

## Завдання

### Обрана предметна область
DailyMood — застосунок для відстеження настрою з журналом, статистикою, звичками/цілями та магазином цифрових wellness‑ресурсів. Є Premium‑можливості (Mood Predictor, Activity Recommendations), темізація профілю, аватари, адмін‑панелі для керування даними. Зберігаємо користувачів, записи настроїв, продукти, замовлення, платежі, відгуки, звички та цілі.

### Реалізовані вимоги

- [x] Рівень 1: Створено БД (SQLite у dev) з таблицями (зокрема `feedback`), повні CRUD‑операції, адмін‑панель для перегляду/видалення відгуків, магазин з таблицями продуктів та замовлень
- [x] Рівень 2: Додано додаткові таблиці предметної області (Payment, OrderItem, MoodEntry з прив'язкою до користувача, Habit, HabitCompletion, MonthlyGoal) та інтегровано в застосунок і адмін‑панелі
- [x] Рівень 3: Дві суттєві функції — Premium Activity Recommendations та Mood Predictor (+ експорт журналу у CSV/JSON, розширена статистика)

## Хід виконання роботи

### Підготовка середовища розробки
- Python 3.9+ (локально dev)
- Бібліотеки: Flask 2.x, Flask‑SQLAlchemy 3.x
- Інші: `python-dotenv` (опційно), PowerShell для запуску, SQLite (dev)

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
└── data/                   
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
- Прив'язка `MoodEntry.user_id` (власник бачить лише свої записи) + автоматична міграція існуючих записів
- Order ↔ Payment — зв'язок 1:1; User → Order — 1:N; Order → OrderItem — 1:N


### Опис реалізованої функціональності

#### Система відгуків
- API: `POST /api/feedback`, `GET /api/feedback`, `DELETE /api/feedback/<id>` (admin)
- Адмін‑панель: перегляд/видалення останніх 50 відгуків

#### Магазин (без «корзини»)
- Каталог продуктів: `GET /api/products` (активні для всіх, всі для адміна)
- Створення замовлення: `POST /api/orders` (масив товарів)
- Оплата: `POST /api/payments` (методи `card`, `online_banking`, `paypal`), генерація `transaction_id`, зміна статусів
- Авто‑активація Premium за цифрові продукти (ключові слова "premium/преміум")

#### Адміністративна панель
- Розділи: users, products, orders, feedback
- Дії: призначення ролей/преміум, CRUD продуктів, зміна статусів замовлень, видалення відгуків

#### Додатково (Premium/аналітика)
- Activity Recommendations: персональні поради за настроєм
- Mood Predictor: простий ML‑алгоритм на основі трендів і дня тижня
- Журнал: експорт CSV/JSON, фільтри, власність записів
- Статистика: розподіл і тренди за 30 днів/рік

## Ключові фрагменти коду

### Моделі (фрагмент SQLAlchemy)
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

### CRUD/маршрути (фрагменти)
```python
@app.route('/api/feedback', methods=['POST'])
def create_feedback(): ...

@app.route('/api/products', methods=['GET'])
def get_products(): ...

@app.route('/api/orders', methods=['POST'])
@login_required
def create_order(): ...

@app.route('/api/payments', methods=['POST'])
@login_required
def create_payment(): ...
```

### Зв'язки (Order з Item і Payment)
```python
class Order(db.Model):
	items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')
	# backref payment (uselist=False) у Payment
```

## Розподіл обов'язків
- Ярослав: повна розробка бекенду/фронтенду/БД, преміум‑логіка, адмін‑панелі, документація архітектури
- Настя: звіти lab04, README.md
- Аліна: консультації по дизайну, пропозиції UI‑покращень
- Антон: тестування інтерфейсу (кнопки, форми)

## Скріншоти
- Форма відгуку — 
![POST feedback](lab-reports\screenshot\feedback.png)
- Каталог продуктів / Оплата — 
![POST catalog](lab-reports\screenshot\catalog.png)
- Адмін‑панель — 
![POST admin_panel](lab-reports\screenshot\admin_panel.png)
- Статистика/Mood Predictor — 
![]	
## Тестування
1. Додавання відгуку та перегляд у адмін‑панелі
2. Створення замовлення і проведення «оплати» у демо‑режимі
3. CRUD продуктів (адмін), зміна статусів замовлень
4. Перевірка приватності журналу (видимість лише своїх записів)
5. Експорт журналу у CSV/JSON

## Висновки
- Реалізовано повноцінну БД з бізнес‑логікою магазину та преміум‑функціями
- Отримані навички: проектування схеми, робота з ORM, проєктування API, безпечна обробка даних, аналітика
- Труднощі: усунення копіпасти у `create_habit`, міграція `MoodEntry.user_id`, узгодження тем/ролей
- Подальші кроки: реальний платіжний шлюз, email‑верифікація, розширення настроїв (anxious), Alembic‑міграції

Очікувана оцінка: **11–12 балів**  
Обґрунтування: виконано всі рівні, додано преміум‑можливості, виправлено критичні проблеми, якісна документація

