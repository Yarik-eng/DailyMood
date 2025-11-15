# DailyMood 3.0 — Архітектура та Логіка

## Загальний Огляд
**DailyMood** — Flask додаток для трекінгу настрою з магазином wellness-ресурсів, Premium підпискою та персоналізованими рекомендаціями.

---

## Технологічний Стек
- **Backend:** Flask 2.x + SQLAlchemy ORM
- **Database:** PostgreSQL (production) / SQLite (dev)
- **Frontend:** Vanilla JS, CSS з темізацією через CSS variables
- **Auth:** Session-based з `@login_required` декоратором
- **Payment:** Demo режим (card, online_banking, paypal)

---

## Моделі Бази Даних

### 1. User
**Файл:** `models.py`  
**Таблиця:** `users`

```python
id: Integer (PK)
email: String(255) — унікальний
password_hash: String(255)
is_admin: Boolean (default=False)
is_premium: Boolean (default=False)
premium_started_at: DateTime (nullable)
premium_expires_at: DateTime (nullable)
created_at: DateTime
avatar: String(255) (nullable)
```

**Зв'язки:**
- `orders` → One-to-Many з `Order`

**Методи:**
- `set_password(password)` — генерує хеш
- `check_password(password)` — перевіряє хеш
- `to_dict()` — JSON без пароля

---

### 2. Product
**Файл:** `models.py`  
**Таблиця:** `products`

```python
id: Integer (PK)
name: String(200)
slug: String(200) — унікальний
type: String(50) — quote_pack, theme, journal_template, habit_course
description: Text
price: Float
is_active: Boolean (default=True)
created_at: DateTime
```

**Зв'язки:**
- `order_items` → One-to-Many з `OrderItem`

**Приклад типів продуктів:**
- `premium_subscription` — цифровий продукт, активує `is_premium`
- `theme` — кастомна тема
- `quote_pack` — пакет цитат

---

### 3. Order
**Файл:** `models.py`  
**Таблиця:** `orders`

```python
id: Integer (PK)
user_id: Integer (FK → users.id)
status: String(50) — new, processing, completed, canceled
total_amount: Float
created_at: DateTime
updated_at: DateTime
```

**Зв'язки:**
- `user` → Many-to-One з `User`
- `items` → One-to-Many з `OrderItem`
- `payment` → One-to-One з `Payment`

**Методи:**
- `calculate_total()` — сума з `OrderItem.subtotal`

---

### 4. OrderItem
**Файл:** `models.py`  
**Таблиця:** `order_items`

```python
id: Integer (PK)
order_id: Integer (FK → orders.id)
product_id: Integer (FK → products.id)
quantity: Integer (default=1)
unit_price: Float — ціна на момент покупки
subtotal: Float — quantity * unit_price
```

**Зв'язки:**
- `order` → Many-to-One з `Order`
- `product` → Many-to-One з `Product`

---

### 5. Payment
**Файл:** `models.py`  
**Таблиця:** `payments`

```python
id: Integer (PK)
order_id: Integer (FK → orders.id, unique)
payment_method: String(50) — card, online_banking, paypal
status: String(50) — pending, completed, failed, refunded
amount: Float
transaction_id: String(255) — унікальний ID транзакції
card_last4: String(4) (nullable)
card_brand: String(20) (nullable) — Visa, Mastercard
payment_details: Text (nullable) — JSON з додатковими даними
created_at: DateTime
completed_at: DateTime (nullable)
```

**Зв'язки:**
- `order` → One-to-One з `Order`

---

### 6. MoodEntry
**Файл:** `models.py`  
**Таблиця:** `mood_entries`

```python
id: Integer (PK)
mood: String(32) — VALID_MOODS = ['happy', 'neutral', 'sad']
date: Date
title: String(200)
content: Text (nullable)
activities: String(500) (nullable) — comma-separated
created_at: DateTime
```

**Методи:**
- `get_mood_emoji()` — повертає 😊 / 😐 / 😢
- `to_dict()` — конвертує activities у масив

---

### 7. Feedback
**Файл:** `models.py`  
**Таблиця:** `feedback`

```python
id: Integer (PK)
name: String(120) (nullable)
email: String(255) (nullable)
message: Text
rating: Integer (nullable) — 1-5
created_at: DateTime
```

---

## Ключові API Маршрути

### Аутентифікація
**Файл:** `app.py`

#### `POST/GET /auth/register`
- **GET:** Показує форму реєстрації
- **POST:** Створює користувача, хешує пароль, встановлює сесію
- **Логіка:** 
  - Перевірка email на унікальність
  - `user.set_password(password)` → bcrypt hash
  - `session['user_id'] = user.id`

#### `POST/GET /auth/login`
- **GET:** Показує форму входу
- **POST:** Перевіряє email/password, встановлює сесію
- **Логіка:**
  - `user.check_password(password)` → bcrypt verify
  - `session['user_id'] = user.id`

#### `POST /auth/logout`
- Очищує `session['user_id']`
- Redirect на головну

---

### Магазин та Замовлення

#### `GET /api/products`
- Повертає всі активні продукти (`is_active=True`)

#### `POST /api/orders`
- **Body:** `{ items: [{product_id, quantity}] }`
- **Логіка:**
  1. Створює `Order` зі статусом `new`
  2. Для кожного item створює `OrderItem` з `unit_price` і `subtotal`
  3. Викликає `order.calculate_total()`
  4. Зберігає в БД

#### `POST /api/payments`
- **Body:** `{ order_id, payment_method, card_number?, card_expiry?, card_cvv? }`
- **Логіка:**
  1. Створює `Payment` зі статусом `pending`
  2. **Card:** зберігає `card_last4`, `card_brand`, генерує `transaction_id`
  3. **PayPal:** генерує `transaction_id = PP-xxx`, статус `completed`
  4. **Online banking:** `transaction_id = OB-xxx`
  5. Якщо продукт містить "premium/преміум" → `user.is_premium = True`
  6. Для цифрових продуктів → `order.status = completed`
  7. Для фізичних → `order.status = processing`

**Методи оплати:**
```python
['card', 'online_banking', 'paypal']
```

---

### Premium Функції

#### `GET /api/premium/activity-recommendations`
- **Доступ:** Тільки `@login_required` + `user.is_premium`
- **Параметри:** `?mood=happy|neutral|sad` (опціонально)
- **Логіка:**
  1. Якщо `mood` не передано → бере останній `MoodEntry.mood`
  2. За замовчуванням → `neutral`
  3. Повертає з словника `recommendations[mood]`:
     - `title` — заголовок
     - `activities[]` — масив з `icon, name, description, duration`
     - `tip` — порада
     - `current_mood`, `mood_emoji`

**Приклад відповіді:**
```json
{
  "status": "success",
  "title": "Ти у чудовому настрої! 🌟",
  "activities": [
    {
      "icon": "🎨",
      "name": "Творчість",
      "description": "Малюй, пиши, створюй щось нове!",
      "duration": "30-60 хв"
    }
  ],
  "tip": "Використай цю позитивну енергію для справ, які давно відкладав!",
  "current_mood": "happy",
  "mood_emoji": "😊"
}
```

---

### Журнал Настроїв

#### `GET /api/entries`
- **Query Params:** `year`, `month`, `mood`
- Фільтрує `MoodEntry` за параметрами
- Повертає масив записів у форматі `to_dict()`

#### `POST /api/entries`
- **Body:** `{ mood, date, title, content?, activities? }`
- **Валідація:** `mood` мусить бути в `MoodEntry.VALID_MOODS`
- Створює новий `MoodEntry`

#### `PUT /api/entries/<id>`
- Оновлює існуючий запис

#### `DELETE /api/entries/<id>`
- Видаляє запис

---

### Статистика

#### `GET /api/statistics`
- Агрегує дані за останній місяць:
  - **mood_distribution:** `{ happy: count, neutral: count, sad: count }`
  - **mood_trend:** масив `[{date, mood, emoji}]` за 30 днів
  - **most_common_mood:** найчастіший настрій
- **SQL:** `GROUP BY MoodEntry.mood`, `func.count()`

---

## Frontend Архітектура

### Темізація
**Файл:** `templates/base.html`

**Механіка:**
- Атрибут `data-theme="dark|light"` на `<html>`
- Атрибут `data-profile-theme="default|pink|purple|..."` на `<html>`
- CSS змінні: `--profile-accent`, `--profile-glow`

**Теми профілю:**
- **Free (4):** default, pink, green, rose, orange, mint, slate
- **Premium (12):** purple, teal, sunset, galaxy, forest, crimson, deepsea, gold, lavender, coral, amber

**Логіка доступу:**
```javascript
function updatePremiumThemesAccess() {
  if (user.is_premium) {
    // input.disabled = false, badge = '★'
  } else {
    // input.disabled = true, badge = '🔒'
  }
}
```

**Збереження:**
- `localStorage.setItem('theme', 'dark')`
- `localStorage.setItem('profileTheme', 'purple')`

---

### Activity Recommendations UI
**Файл:** `templates/index.html`

**Потік:**
1. `initActivityRecs()` викликається при завантаженні сторінки
2. Fetch `/api/me` → перевіряє `user.is_premium`
3. Якщо не Premium → показує "🔒 Доступно тільки для Premium"
4. Якщо Premium → fetch `/api/premium/activity-recommendations`
5. Рендерить картки активностей у `#recsActivities`

**UI структура:**
```html
<section id="activityRecsSection">
  <h2>🎯 Activity Recommendations <span>PREMIUM</span></h2>
  <div id="recsLocked">🔒 Оновіть до Premium...</div>
  <div id="recsContent">
    <h3 id="recsMoodTitle"></h3>
    <div id="recsActivities"></div>
    <p id="recsTip"></p>
  </div>
  <div id="recsError"></div>
</section>
```

---

## Логіка Зв'язків (Relationships)

### User → Orders → OrderItems → Products
```
User (1) ──→ (N) Order
Order (1) ──→ (N) OrderItem
OrderItem (N) ──→ (1) Product
```

**Приклад потоку покупки:**
1. Користувач додає `Product` у кошик
2. Створюється `Order` з `user_id`
3. Для кожного товару створюється `OrderItem` з `product_id`, `quantity`, `unit_price`
4. `Order.calculate_total()` сумує всі `OrderItem.subtotal`
5. Створюється `Payment` з `order_id`
6. Якщо оплата успішна → `order.status = completed`
7. Якщо продукт Premium → `user.is_premium = True`

### Order ↔ Payment (One-to-One)
```
Order (1) ←→ (1) Payment
```
- `order_id` у `Payment` є `UNIQUE`
- Cascade delete: видалення `Order` → видаляє `Payment`

### MoodEntry (Standalone)
- Не прив'язаний до `User` (глобальні записи для всіх)
- Можна розширити: додати `user_id` для персональних записів

---

## Ключові Бізнес-Правила

### Premium Активація
**Файл:** `app.py` → `create_payment()`

```python
# Перевірка чи є digital Premium product
for item in order.items:
    if 'premium' in item.product.name.lower() or 'преміум' in item.product.name.lower():
        user.is_premium = True
        user.premium_started_at = datetime.utcnow()
        break

# Статус замовлення
if has_digital_product:
    order.status = 'completed'
else:
    order.status = 'processing'
```

### Валідація Настроїв
**Файл:** `models.py` → `MoodEntry.__init__()`

```python
VALID_MOODS = ['happy', 'neutral', 'sad']

if mood not in self.VALID_MOODS:
    raise ValueError(f'Недійсне значення настрою. Допустимі: {", ".join(self.VALID_MOODS)}')
```

### Рекомендації за Настроєм
**Файл:** `app.py` → `activity_recommendations()`

**Логіка вибору настрою:**
1. `request.args.get('mood')` — якщо передано параметр
2. `MoodEntry.query.order_by(date.desc()).first().mood` — останній запис
3. `'neutral'` — за замовчуванням

---

## Розширення Системи

### Додати Новий Настрій (наприклад, "anxious")

1. **Оновити модель:**
```python
# models.py
VALID_MOODS = ['happy', 'neutral', 'sad', 'anxious']
```

2. **Додати рекомендації:**
```python
# app.py → activity_recommendations()
recommendations = {
    'anxious': {
        'title': 'Заспокій розум 🌿',
        'activities': [
            {'icon': '🧘', 'name': 'Дихальні вправи', 'description': '4-7-8 техніка', 'duration': '5-10 хв'},
            # ...
        ],
        'tip': 'Тривога тимчасова. Зроби глибокий вдих.'
    }
}
```

3. **Додати емодзі:**
```python
emoji_map = {
    'happy': '😊',
    'neutral': '😐',
    'sad': '😢',
    'anxious': '😰'
}
```

4. **Оновити UI селектор настроїв у формі журналу**

---

### Додати User-Specific MoodEntries

**Зміни в моделі:**
```python
# models.py
class MoodEntry(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref='mood_entries')
```

**Зміни в API:**
```python
# app.py
@login_required
def create_entry():
    entry = MoodEntry(
        mood=data['mood'],
        user_id=session['user_id'],  # Прив'язка до користувача
        ...
    )
```

---

### Додати Premium Expiration Logic

**Файл:** `app.py`

```python
from datetime import datetime, timedelta

# При активації Premium
user.premium_started_at = datetime.utcnow()
user.premium_expires_at = datetime.utcnow() + timedelta(days=30)

# Перевірка перед доступом
if user.is_premium and user.premium_expires_at < datetime.utcnow():
    user.is_premium = False
```

---

## Середовище та Конфігурація

### Environment Variables
**Файл:** `.env` (не в репозиторії)

```bash
DATABASE_URL=postgresql://user:password@localhost/dailymood
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
```

### Конфігурація Flask
**Файл:** `app.py`

```python
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dailymood.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
```

---

## Команди для Розробки

### Запуск сервера
```bash
python app.py
```
або
```bash
run.bat
```

### Ініціалізація БД
```bash
python scripts/init_db.py
```

### Додати тестові продукти
```bash
python scripts/seed_products.py
```

---

## Відомі Обмеження та TODO

### Поточні Обмеження
- Demo payment (без реальної інтеграції Stripe/PayPal API)
- Немає email підтвердження при реєстрації
- `MoodEntry` глобальні (не прив'язані до користувачів)
- Немає логіки експірації Premium підписки

### Плани на Майбутнє
- [ ] Додати настрій "anxious" з порадами
- [ ] Прив'язати `MoodEntry` до `User`
- [ ] Додати email верифікацію
- [ ] Інтегрувати Stripe для реальних платежів
- [ ] Додати систему нагадувань (Push notifications)
- [ ] Експорт даних у PDF/CSV
- [ ] Mood Predictor на основі ML

---

## Структура Файлів

```
DailyMood3.0/
├── app.py                  # Головний Flask додаток
├── models.py               # SQLAlchemy моделі
├── requirements.txt        # Python залежності
├── run.bat                 # Windows launcher
├── ARCHITECTURE.md         # Цей файл
├── scripts/
│   ├── init_db.py         # Ініціалізація БД
│   └── seed_products.py   # Тестові продукти
├── templates/
│   ├── base.html          # Базовий шаблон + теми
│   ├── index.html         # Головна + Activity Recs
│   ├── register.html      # Реєстрація
│   ├── login.html         # Вхід
│   ├── store.html         # Магазин
│   ├── journal.html       # Журнал настроїв
│   ├── statistics.html    # Статистика
│   ├── goals.html         # Цілі
│   ├── about.html         # Про нас + фідбек
│   └── favorites.html     # Обране
├── static/
│   ├── style.css          # Головні стилі
│   ├── script.js          # Головний JS
│   ├── css/
│   │   ├── goals.css
│   │   └── transitions.css
│   ├── js/
│   │   └── i18n.js        # Інтернаціоналізація
│   └── translations/
│       ├── en.js
│       ├── uk.js
│       └── quotes.js
└── data/                   # SQLite DB (gitignored)
```

---

## Детальний Опис Файлів

### Кореневий Рівень

#### `app.py`
**Призначення:** Головний файл Flask додатку  
**Задачі:**
- Ініціалізація Flask app та SQLAlchemy
- Конфігурація БД (`DATABASE_URL`, `SECRET_KEY`)
- Визначення всіх API маршрутів:
  - `/auth/*` — реєстрація, вхід, вихід
  - `/api/entries` — CRUD операції з записами настрою
  - `/api/products` — отримання списку продуктів
  - `/api/orders` — створення замовлень
  - `/api/payments` — обробка платежів
  - `/api/premium/activity-recommendations` — рекомендації для Premium
  - `/api/statistics` — агрегація даних за настроями
  - `/api/feedback` — збереження відгуків
  - `/api/me` — отримання даних поточного користувача
- Логіка Premium активації при оплаті
- Декоратор `@login_required` для захисту маршрутів
- Запуск dev-сервера (`if __name__ == '__main__'`)

**Залежності:** `models.py`, Flask, SQLAlchemy, bcrypt

---

#### `models.py`
**Призначення:** Визначення структури бази даних  
**Задачі:**
- Моделі SQLAlchemy для всіх таблиць:
  - `User` — користувачі з хешуванням паролів
  - `Product` — товари магазину
  - `Order` — замовлення користувачів
  - `OrderItem` — позиції у замовленні
  - `Payment` — інформація про платежі
  - `MoodEntry` — записи настроїв
  - `Feedback` — відгуки користувачів
- Relationships (зв'язки між таблицями)
- Методи моделей:
  - `set_password()`, `check_password()` — робота з паролями
  - `to_dict()` — серіалізація у JSON
  - `calculate_total()` — підрахунок суми замовлення
- Константи: `VALID_MOODS = ['happy', 'neutral', 'sad']`

**Залежності:** Flask-SQLAlchemy, werkzeug.security

---

#### `requirements.txt`
**Призначення:** Список Python залежностей  
**Задачі:**
- Визначає версії пакетів для проєкту
- Використовується для встановлення: `pip install -r requirements.txt`

**Основні пакети:**
```
Flask==2.x
Flask-SQLAlchemy==3.x
psycopg2-binary  # PostgreSQL driver
python-dotenv    # Завантаження .env
```

---

#### `run.bat`
**Призначення:** Windows launcher для швидкого запуску  
**Задачі:**
- Активація Python environment (якщо є)
- Запуск `python app.py`
- Спрощує запуск для Windows користувачів

---

### Директорія `scripts/`

#### `scripts/init_db.py`
**Призначення:** Ініціалізація бази даних  
**Задачі:**
- Видалення старих таблиць (`db.drop_all()`)
- Створення нових таблиць (`db.create_all()`)
- Створення admin користувача за замовчуванням
- Запускається вручну перед першим використанням

**Використання:**
```bash
python scripts/init_db.py
```

---

#### `scripts/seed_products.py`
**Призначення:** Додавання тестових продуктів  
**Задачі:**
- Створення зразкових товарів для магазину:
  - Premium підписка
  - Quote packs
  - Themes
  - Journal templates
- Заповнення БД демо-даними для розробки

**Використання:**
```bash
python scripts/seed_products.py
```

---

### Директорія `templates/`

#### `templates/base.html`
**Призначення:** Базовий шаблон для всіх сторінок  
**Задачі:**
- HTML структура (`<head>`, навігація, footer)
- Визначення блоків для дочірніх шаблонів: `{% block content %}`
- **Система темізації:**
  - CSS змінні для 17 тем (4 Free + 13 Premium)
  - Логіка перемикання dark/light режиму
  - Customization drawer (шухляда налаштувань)
- **JavaScript функції:**
  - `updatePremiumThemesAccess()` — контроль доступу до Premium тем
  - `initProfileThemeRadios()` — ініціалізація селектора тем
  - Theme persistence у `localStorage`
- Навігаційне меню з перевіркою авторизації
- Мобільна адаптивність

**CSS змінні теми:**
```css
--profile-accent: #3b82f6;
--profile-glow: rgba(59, 130, 246, 0.3);
```

---

#### `templates/index.html`
**Призначення:** Головна сторінка  
**Задачі:**
- Привітання користувача
- **Activity Recommendations секція (Premium):**
  - Перевірка Premium статусу через `/api/me`
  - Завантаження рекомендацій через API
  - Рендер карток активностей
  - Відображення locked state для Free користувачів
- Мотиваційні цитати
- Швидкі посилання на основні розділи
- **JavaScript функції:**
  - `initActivityRecs()` — ініціалізація рекомендацій
  - Динамічний рендер UI на основі Premium статусу

---

#### `templates/register.html`
**Призначення:** Сторінка реєстрації  
**Задачі:**
- Форма з полями `email`, `password`, `confirmPassword`
- Валідація на frontend:
  - Перевірка формату email
  - Співпадіння паролів
  - Мінімальна довжина пароля
- POST запит до `/auth/register`
- Редирект на `/auth/login` після успіху
- Посилання на сторінку входу
- Стилізація з theme-aware контрастом (`.auth-form-input`)

---

#### `templates/login.html`
**Призначення:** Сторінка входу  
**Задачі:**
- Форма з полями `email`, `password`
- POST запит до `/auth/login`
- Редирект на головну після успіху
- Відображення помилок (неправильний email/пароль)
- Посилання на сторінку реєстрації
- Стилізація з theme-aware контрастом

---

#### `templates/store.html`
**Призначення:** Магазин wellness-ресурсів  
**Задачі:**
- Завантаження продуктів через `/api/products`
- Відображення карток товарів з:
  - Назва, опис, ціна
  - Кнопка "Додати до кошика"
- **Корзина покупок:**
  - Додавання/видалення товарів
  - Підрахунок загальної суми
  - localStorage для збереження корзини
- **Checkout форма:**
  - Вибір методу оплати (card, online_banking, paypal)
  - Поля для карти (номер, expiry, CVV)
  - Створення замовлення через `/api/orders`
  - Обробка платежу через `/api/payments`
- Відображення статусу оплати
- Таблиця порівняння Free vs Premium

---

#### `templates/journal.html`
**Призначення:** Журнал настроїв  
**Задачі:**
- **Форма створення запису:**
  - Вибір настрою (happy, neutral, sad)
  - Дата, заголовок, контент
  - Теги активностей
- **Список записів:**
  - Завантаження через `/api/entries`
  - Фільтрація за місяцем, роком, настроєм
  - Редагування та видалення записів
- **UI елементи:**
  - Емодзі для кожного настрою
  - Адаптивна сітка карток
  - Модальні вікна для редагування
- CRUD операції через API

---

#### `templates/statistics.html`
**Призначення:** Візуалізація статистики настроїв  
**Задачі:**
- Завантаження даних через `/api/statistics`
- **Графіки та діаграми:**
  - Mood distribution (розподіл настроїв)
  - Mood trend (тренд за 30 днів)
  - Most common mood (найчастіший настрій)
- **Візуалізація:**
  - Pie chart або bar chart (можливо Chart.js)
  - Timeline настроїв
  - Відсотки та кількість
- Експорт даних (майбутня фіча)

---

#### `templates/goals.html`
**Призначення:** Управління цілями користувача  
**Задачі:**
- Створення нових цілей
- Список активних цілей
- Відстеження прогресу
- Позначення цілей як виконані
- localStorage для збереження (або API у майбутньому)

**Окремі стилі:** `static/css/goals.css`

---

#### `templates/about.html`
**Призначення:** Інформація про проєкт + форма зворотного зв'язку  
**Задачі:**
- Опис DailyMood, місія, цінності
- **Feedback форма:**
  - Поля: ім'я, email, повідомлення, рейтинг (1-5 ⭐)
  - POST запит до `/api/feedback`
  - Відображення успіху/помилки
- Контактна інформація
- **Стилізація форми:**
  - `.feedback-input`, `.feedback-select`
  - Theme-aware контраст для темної/світлої теми
  - Star emoji у рейтингу

---

#### `templates/favorites.html`
**Призначення:** Збережені улюблені елементи  
**Задачі:**
- Список улюблених цитат
- Список улюблених записів настрою
- Додавання/видалення з обраного
- localStorage для збереження

---

#### `templates/admin_products.html`
**Призначення:** Адмін-панель для управління продуктами  
**Задачі:**
- Доступ тільки для `is_admin = True`
- **CRUD операції з продуктами:**
  - Створення нового товару
  - Редагування існуючого
  - Видалення товару
  - Деактивація (`is_active = False`)
- **Форма полів:**
  - Name, slug, type, price, description
  - `.admin-input`, `.admin-textarea` стилі з theme контрастом
- Список всіх продуктів у таблиці

---

### Директорія `static/`

#### `static/style.css`
**Призначення:** Головні глобальні стилі  
**Задачі:**
- CSS для базового layout (flexbox, grid)
- Типографія (шрифти, розміри)
- Кольорова схема темної теми (default)
- **Компоненти:**
  - Buttons, inputs, cards
  - Navigation bar
  - Modals, drawers
- Responsive breakpoints (mobile, tablet, desktop)
- Анімації та transitions
- Theme variables (використовує змінні з `base.html`)

---

#### `static/script.js`
**Призначення:** Загальний JavaScript для всіх сторінок  
**Задачі:**
- Ініціалізація глобальних функцій
- Helpers для API запитів
- Toast notifications
- Модальні вікна
- LocalStorage utilities
- Event listeners для загальних UI елементів
- Може містити shared функції типу `formatDate()`, `showError()`

---

#### `static/css/goals.css`
**Призначення:** Специфічні стилі для сторінки Цілей  
**Задачі:**
- Layout для goal cards
- Progress bars
- Стилі для checkbox/радіо кнопок
- Анімації completion
- Responsive дизайн для goals grid

---

#### `static/css/transitions.css`
**Призначення:** Анімації переходів між елементами  
**Задачі:**
- Fade in/out
- Slide animations
- Page transitions
- Hover effects
- Loading spinners

---

#### `static/js/i18n.js`
**Призначення:** Інтернаціоналізація (багатомовність)  
**Задачі:**
- Завантаження перекладів з `translations/`
- Функція `translatePage(lang)` — перемикання мови
- Заміна `data-i18n` атрибутів у HTML
- Збереження вибраної мови у `localStorage`
- Динамічна зміна контенту без перезавантаження

**Приклад:**
```javascript
function translatePage(lang) {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = translations[lang][key];
  });
}
```

---

#### `static/translations/en.js`
**Призначення:** Англійські переклади  
**Задачі:**
- Об'єкт з ключами перекладів:
```javascript
const translations_en = {
  'welcome': 'Welcome',
  'activity_recs_title': 'Activity Recommendations',
  'feature_recommendations': 'Activity Recommendations',
  // ...
};
```
- Експортується для `i18n.js`

---

#### `static/translations/uk.js`
**Призначення:** Українські переклади  
**Задачі:**
- Об'єкт з українськими строками:
```javascript
const translations_uk = {
  'welcome': 'Ласкаво просимо',
  'activity_recs_title': 'Activity Recommendations',
  'recs_loading': 'Завантаження рекомендацій...',
  // ...
};
```

---

#### `static/translations/quotes.js`
**Призначення:** База мотиваційних цитат  
**Задачі:**
- Масив об'єктів з цитатами:
```javascript
const quotes = [
  { text: "Believe in yourself", author: "Unknown", mood: "happy" },
  { text: "One step at a time", author: "Lao Tzu", mood: "neutral" },
  // ...
];
```
- Випадковий вибір для відображення
- Фільтрація за настроєм
- Експорт для інших модулів

---

### Директорія `data/`
**Призначення:** Зберігання SQLite бази даних  
**Задачі:**
- Файл `dailymood.db` (не в git)
- Використовується у dev режимі
- Production використовує PostgreSQL

---

### Додаткові Файли (не показані у структурі)

#### `.env`
**Призначення:** Environment змінні (не в репозиторії)  
**Задачі:**
- `DATABASE_URL` — connection string до БД
- `SECRET_KEY` — Flask secret для sessions
- `FLASK_ENV=development|production`

#### `.gitignore`
**Призначення:** Виключення файлів з git  
**Задачі:**
- `__pycache__/`, `*.pyc` — Python кеш
- `.env` — секрети
- `data/` — локальна БД
- `venv/`, `env/` — virtual environments

#### `README.md`
**Призначення:** Документація проєкту  
**Задачі:**
- Опис проєкту
- Інструкції по встановленню
- Команди для запуску
- Screenshots
- License info

---

### Приховані/Backup Файли

#### `app.py.bak`, `app.py.old`
**Призначення:** Резервні копії `app.py`  
**Задачі:**
- Збереження попередніх версій коду перед рефакторингом
- Можна видалити після успішного тестування

#### `templates/index.html.bak`
**Призначення:** Резервна копія `index.html`  
**Задачі:** Аналогічно до backup файлів

---

## Контакти та Підтримка
- **Repository:** github.com/Yarik-eng/DailyMood
- **Branch:** main
- **Python:** 3.9+
- **Flask:** 2.x

---

**Останнє оновлення:** 2025-11-15
