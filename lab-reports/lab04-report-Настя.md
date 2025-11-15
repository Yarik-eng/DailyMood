# Звіт з лабораторної роботи 4

## Реалізація бази даних для вебпроєкту DailyMood 3.0

### Інформація про команду
- Назва команди: Ctrl+V
- Автор звіту: Мирон Настя
- Роль: Документатор (підготовка звітів, README.md)

#### Склад команди
- Ярослав Мерчук — лідер, full‑stack розробник
- Мирон Настя — документатор (цей звіт, README.md)
- Кутецька Аліна — UI/UX (консультації по дизайну, ідеї покращення UI)
- Приступа Антон — тестувальник (перевірка інтерфейсу)

## Завдання

### Обрана предметна область
DailyMood — застосунок для відстеження настрою з журналом, статистикою, звичками/цілями та магазином цифрових wellness‑ресурсів. Є Premium‑функції та адмін‑панелі.

### Реалізовані вимоги
- [x] Рівень 1: БД + CRUD + адмін‑панель відгуків + магазин (продукти/замовлення)
- [x] Рівень 2: Додаткові таблиці предметної області (Payment, OrderItem, MoodEntry з user_id, Habit, HabitCompletion, MonthlyGoal)
- [x] Рівень 3: Activity Recommendations та Mood Predictor (+ експорт журналу, статистика)

## Хід виконання роботи

### Підготовка середовища
- Python 3.9+, Flask 2.x, Flask‑SQLAlchemy 3.x
- Розгортання: `pip install -r requirements.txt`, `python scripts/init_db.py`, `python app.py`

### Структура проєкту
```
DailyMood3.0/
├── app.py               
├── models.py             
├── requirements.txt     
├── run.bat               
├── ARCHITECTURE.md        
└── scripts/
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
- Прив'язка `MoodEntry.user_id` (власник бачить лише свої записи)
- Order ↔ Payment — 1:1; User → Order — 1:N; Order → OrderItem — 1:N

### Опис реалізованої функціональності
- Відгуки: створення/перегляд/видалення (admin)
- Магазин: список продуктів → створення замовлень → «оплата» (card/online_banking/paypal)
- Адмін: користувачі/продукти/замовлення/відгуки
- Premium: рекомендації та прогноз настрою

## Ключові фрагменти коду (приклади)
```python
@app.route('/api/feedback', methods=['POST'])
def create_feedback(): ...
```

## Розподіл обов'язків
- Ярослав: уся кодова частина та БД
- Настя: підготовка звітів lab04, написання README.md
- Аліна: консультації по дизайну, пропозиції UI‑покращень
- Антон: тестування інтерфейсу

## Скріншоти
- Форма відгуку — 
![alt text](image-1.png)
- Каталог продуктів / Оплата — 
![alt text](image-2.png)
![alt text](image-3.png)
- Адмін‑панель — 
![alt text](image-4.png)
- Статистика/Mood Predictor — 
![alt text](image-5.png)

## Тестування
1. Додавання нового відгуку та перегляд у адмін‑панелі
2. Створення замовлення і демо‑«оплата» (card/online_banking/paypal)
3. CRUD продуктів (адмін), зміна статусів замовлень
4. Перевірка приватності журналу (видимість лише своїх записів)
5. Експорт журналу у CSV/JSON

## Висновки
- Реалізовано предметну область з Premium‑можливостями та адмін‑інструментами; додано документацію

Очікувана оцінка: **10–11 балів**

