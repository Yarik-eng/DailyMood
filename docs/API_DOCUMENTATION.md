# DailyMood REST API Documentation

## Огляд

DailyMood API надає RESTful інтерфейс для роботи з щоденником настрою, звичок, цілей та магазином Premium контенту.

**Базовий URL:** `http://localhost:5000`  
**Формат даних:** JSON  
**Авторизація:** Session-based (Flask session cookies)

## Інтерактивна документація

Після запуску сервера доступна повна інтерактивна документація Swagger UI:

**Swagger UI:** [http://localhost:5000/api/docs](http://localhost:5000/api/docs)

## Швидкий старт

### 1. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 2. Запуск сервера

```bash
python app.py
```

Сервер запуститься на `http://localhost:5000`

### 3. Тестування в Postman

Імпортуйте колекцію Postman з файлу `postman/DailyMood_API.postman_collection.json`

---

## Endpoints

### Products (Продукти)

#### GET /api/products
Отримати список усіх активних продуктів.

**Авторизація:** Ні  
**Параметри:** Немає

**Відповідь 200:**
```json
[
  {
    "id": 1,
    "name": "Premium підписка",
    "description": "Отримайте доступ до всіх преміум-функцій",
    "price": 99.0,
    "type": "subscription",
    "slug": "premium-subscription",
    "is_active": true,
    "created_at": "2025-11-13T20:36:30.844076"
  }
]
```

---

### Orders (Замовлення)

#### POST /api/orders
Створити нове замовлення з одним або кількома товарами.

**Авторизація:** Так (потрібен login)  
**Content-Type:** `application/json`

**Тіло запиту:**
```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 1
    }
  ]
}
```

**Відповідь 201:**
```json
{
  "status": "success",
  "message": "Замовлення створено",
  "order": {
    "id": 11,
    "user_id": 1,
    "status": "new",
    "total_amount": 99.0,
    "items": [
      {
        "id": 11,
        "product_id": 1,
        "product_name": "Premium підписка",
        "quantity": 1,
        "unit_price": 99.0,
        "subtotal": 99.0
      }
    ],
    "created_at": "2025-12-01T17:18:58.034561"
  }
}
```

**Помилки:**
- `400` - Порожній список товарів
- `401` - Не авторизовано

---

### Payments (Платежі)

#### GET /api/payments/methods
Отримати доступні методи оплати.

**Авторизація:** Ні  
**Query параметри:**
- `order_id` (integer, обов'язковий) - ID замовлення

**Приклад запиту:**
```
GET /api/payments/methods?order_id=11
```

**Відповідь 200:**
```json
{
  "status": "success",
  "methods": [
    {
      "id": "card",
      "name": "Банківська картка",
      "description": "Visa, Mastercard, American Express",
      "icon": "💳"
    },
    {
      "id": "online_banking",
      "name": "Інтернет-банкінг",
      "description": "Оплата через онлайн-банкінг",
      "icon": "🏦"
    },
    {
      "id": "paypal",
      "name": "PayPal",
      "description": "Швидка оплата через PayPal",
      "icon": "🅿️"
    }
  ]
}
```

---

#### POST /api/payments
Створити платіж для замовлення.

**Авторизація:** Так (потрібен login)  
**Content-Type:** `application/json`

**Тіло запиту (картка):**
```json
{
  "order_id": 11,
  "payment_method": "card",
  "card_number": "4242424242424242",
  "card_holder": "Test User",
  "card_expiry": "12/29",
  "card_cvv": "123"
}
```

**Тіло запиту (PayPal):**
```json
{
  "order_id": 11,
  "payment_method": "paypal"
}
```

**Відповідь 201:**
```json
{
  "status": "success",
  "message": "Платіж створено успішно",
  "payment": {
    "id": 5,
    "order_id": 11,
    "payment_method": "card",
    "amount": 99.0,
    "status": "completed",
    "transaction_id": "TXN-96350395995B",
    "card_last4": "4242",
    "card_brand": "Unknown",
    "completed_at": "2025-12-01T17:18:58.159317"
  },
  "order": {
    "id": 11,
    "status": "completed",
    "total_amount": 99.0
  }
}
```

**Помилки:**
- `400` - Відсутні обов'язкові поля або невалідний метод оплати
- `401` - Не авторизовано
- `404` - Замовлення не знайдено

**Допустимі методи оплати:**
- `card` - Банківська картка (потрібні: card_number, card_holder, card_expiry, card_cvv)
- `online_banking` - Онлайн-банкінг
- `paypal` - PayPal

---

### Feedback (Відгуки)

#### POST /api/feedback
Створити новий відгук.

**Авторизація:** Ні  
**Content-Type:** `application/json`

**Тіло запиту:**
```json
{
  "name": "Tester",
  "email": "tester@example.com",
  "message": "Great app!",
  "rating": 5
}
```

**Відповідь 200:**
```json
{
  "status": "success",
  "data": {
    "id": 8,
    "name": "Tester",
    "email": "tester@example.com",
    "message": "Great app!",
    "rating": 5,
    "created_at": "2025-12-01T17:18:58.218418"
  }
}
```

**Помилки:**
- `400` - Відсутнє повідомлення або невалідні дані

---

#### GET /api/feedback
Отримати список відгуків.

**Авторизація:** Ні  
**Параметри:** Немає

**Відповідь 200:**
```json
[
  {
    "id": 8,
    "name": "Tester",
    "email": "tester@example.com",
    "message": "Great app!",
    "rating": 5,
    "created_at": "2025-12-01T17:18:58.218418"
  }
]
```

---

### Journal (Щоденник настрою)

#### POST /api/journal
Створити запис настрою.

**Авторизація:** Так (потрібен login)  
**Content-Type:** `application/json`

**Тіло запиту:**
```json
{
  "mood": "happy",
  "date": "2025-11-27",
  "title": "A great day",
  "content": "Felt productive and calm",
  "activities": "reading,exercise"
}
```

**Відповідь 200:**
```json
{
  "status": "success",
  "message": "Запис успішно збережено",
  "data": {
    "id": 10,
    "user_id": 1,
    "mood": "happy",
    "mood_emoji": "😊",
    "date": "2025-11-27",
    "title": "A great day",
    "content": "Felt productive and calm",
    "activities": ["reading", "exercise"],
    "created_at": "2025-12-01T17:18:58.308408"
  }
}
```

**Допустимі значення mood:**
- `happy` - Щасливий 😊
- `calm` - Спокійний 😌
- `energetic` - Енергійний ⚡
- `sad` - Сумний 😢
- `anxious` - Тривожний 😰
- `angry` - Злий 😠
- `tired` - Втомлений 😴

**Помилки:**
- `400` - Відсутні обов'язкові поля (mood, date, title)
- `401` - Не авторизовано

---

## Авторизація

### POST /auth/login
Увійти в систему.

**Content-Type:** `application/json`

**Тіло запиту:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Відповідь 200:**
```json
{
  "status": "success",
  "message": "Успішний вхід",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "is_premium": false
  }
}
```

---

### POST /auth/register
Зареєструвати новий акаунт.

**Content-Type:** `application/json`

**Тіло запиту:**
```json
{
  "email": "newuser@example.com",
  "password": "password123"
}
```

**Відповідь 201:**
```json
{
  "status": "success",
  "message": "Обліковий запис створено",
  "user": {
    "id": 2,
    "email": "newuser@example.com"
  }
}
```

---

### POST /auth/logout
Вийти з системи.

**Відповідь 200:**
```json
{
  "status": "success",
  "message": "Вихід успішний"
}
```

---

## Коди помилок

| Код | Опис |
|-----|------|
| 200 | OK - Запит успішний |
| 201 | Created - Ресурс створено |
| 400 | Bad Request - Невалідні дані |
| 401 | Unauthorized - Потрібна авторизація |
| 403 | Forbidden - Доступ заборонено |
| 404 | Not Found - Ресурс не знайдено |
| 500 | Internal Server Error - Помилка сервера |

## Формат помилок

Всі помилки повертаються у єдиному форматі:

```json
{
  "status": "error",
  "message": "Опис помилки"
}
```

---

## Приклади використання

### Повний флоу покупки Premium підписки

1. **Отримати список продуктів:**
```bash
curl http://localhost:5000/api/products
```

2. **Увійти в систему:**
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}' \
  -c cookies.txt
```

3. **Створити замовлення:**
```bash
curl -X POST http://localhost:5000/api/orders \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"items":[{"product_id":1,"quantity":1}]}'
```

4. **Отримати методи оплати:**
```bash
curl "http://localhost:5000/api/payments/methods?order_id=11"
```

5. **Оплатити замовлення:**
```bash
curl -X POST http://localhost:5000/api/payments \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "order_id": 11,
    "payment_method": "card",
    "card_number": "4242424242424242",
    "card_holder": "Test User",
    "card_expiry": "12/29",
    "card_cvv": "123"
  }'
```

---

## Тестування

### Postman
Імпортуйте колекцію з `postman/DailyMood_API.postman_collection.json`

### Автоматичні тести
```bash
# Запустити функціональні тести
python -m pytest tests/

# Запустити з coverage
python -m pytest --cov=app tests/
```

---

## Версіювання

Поточна версія: **v1.0**

Майбутні версії будуть доступні з префіксом `/api/v2/`

---

## Підтримка

**Email:** support@dailymood.app  
**GitHub:** https://github.com/Yarik-eng/DailyMood

---

## Ліцензія

MIT License
