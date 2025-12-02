# REST API Level 3 - Версії та функції

## Доступні версії API

### API v1 (Базова версія)
**Base URL:** `http://localhost:5000/api/v1`

Підтримує backwards compatibility з існуючими клієнтами. Базова валідація, прості повідомлення про помилки.

**Endpoints:**
- GET `/api/v1/products` - Список продуктів
- POST `/api/v1/orders` - Створити замовлення
- POST `/api/v1/feedback` - Створити відгук

---

### API v2 (Покращена версія) ⭐
**Base URL:** `http://localhost:5000/api/v2`

Розширена версія з повною валідацією, детальними помилками та серіалізацією відповідей.

**Endpoints:**
- GET `/api/v2/products` - Список продуктів з підрахунком
- POST `/api/v2/orders` - Створити замовлення (валідація Marshmallow)
- POST `/api/v2/payments` - Створити платіж (валідація карток)
- POST `/api/v2/feedback` - Створити відгук (валідація email)
- GET `/api/v2/feedback` - Список відгуків
- POST `/api/v2/journal` - Створити запис настрою

---

## Ключові відмінності версій

| Функція | v1 | v2 |
|---------|----|----|
| **Валідація вхідних даних** | Базова | Повна (Marshmallow) |
| **Валідація email** | ❌ | ✅ |
| **Валідація номера картки** | ❌ | ✅ (regex, 13-19 цифр) |
| **Коди помилок** | Прості | Структуровані (code + message) |
| **Серіалізація відповідей** | ❌ | ✅ (Marshmallow schemas) |
| **Підрахунок кількості** | ❌ | ✅ (`count` field) |
| **Детальні помилки** | Один рядок | Об'єкт з `errors` |

---

## Приклади використання

### V1 API (Просто і швидко)

```bash
# Отримати продукти
curl http://localhost:5000/api/v1/products

# Створити відгук (без валідації email)
curl -X POST http://localhost:5000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"invalid-email","message":"Good!"}'
# ✅ Працює навіть з невалідним email
```

---

### V2 API (Безпечно і надійно)

```bash
# Отримати продукти з підрахунком
curl http://localhost:5000/api/v2/products
# Response: {"status":"success","count":5,"data":[...]}

# Створити відгук (з валідацією email)
curl -X POST http://localhost:5000/api/v2/feedback \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"invalid-email","message":"Good!"}'
# ❌ Помилка 400: "errors": {"email": ["Not a valid email address."]}

# Правильний запит
curl -X POST http://localhost:5000/api/v2/feedback \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","message":"Good!","rating":5}'
# ✅ Створено з повною валідацією
```

---

## Коди помилок Level 3

### HTTP Status Codes

| Код | Назва | Опис |
|-----|-------|------|
| 200 | OK | Успішний запит |
| 201 | Created | Ресурс створено |
| 400 | Bad Request | Невалідні дані |
| 401 | Unauthorized | Потрібна авторизація |
| 403 | Forbidden | Доступ заборонено |
| 404 | Not Found | Ресурс не знайдено |
| 405 | Method Not Allowed | HTTP метод не підтримується |
| 422 | Unprocessable Entity | Дані не пройшли валідацію |
| 429 | Too Many Requests | Rate limit перевищено |
| 500 | Internal Server Error | Помилка сервера |
| 503 | Service Unavailable | Сервіс недоступний |

### Error Codes (V2)

| Code | Опис |
|------|------|
| `BAD_REQUEST` | Загальна помилка запиту |
| `VALIDATION_ERROR` | Помилка валідації даних |
| `UNAUTHORIZED` | Не авторизовано |
| `FORBIDDEN` | Доступ заборонено |
| `NOT_FOUND` | Ресурс не знайдено |
| `ORDER_NOT_FOUND` | Замовлення не знайдено |
| `PRODUCT_NOT_FOUND` | Продукт не знайдено |
| `PAYMENT_EXISTS` | Платіж вже існує |
| `MISSING_CARD_FIELDS` | Відсутні поля картки |
| `METHOD_NOT_ALLOWED` | Метод не дозволений |
| `RATE_LIMIT_EXCEEDED` | Перевищено ліміт запитів |
| `INTERNAL_SERVER_ERROR` | Внутрішня помилка сервера |
| `SERVICE_UNAVAILABLE` | Сервіс недоступний |

---

## Формат помилок

### V1 Error Format
```json
{
  "status": "error",
  "message": "Missing message"
}
```

### V2 Error Format
```json
{
  "status": "error",
  "code": "VALIDATION_ERROR",
  "message": "Помилка валідації даних",
  "errors": {
    "email": ["Not a valid email address."],
    "card_number": ["Номер картки повинен містити 13-19 цифр"]
  }
}
```

---

## Валідація даних (V2)

### Email валідація
```python
# Приклад: POST /api/v2/feedback
{
  "email": "test@example.com"  # ✅ Валідний
}
{
  "email": "invalid-email"  # ❌ Помилка валідації
}
```

### Номер картки валідація
```python
# Приклад: POST /api/v2/payments
{
  "card_number": "4242424242424242"  # ✅ 16 цифр
}
{
  "card_number": "123"  # ❌ Менше 13 цифр
}
{
  "card_number": "abcd1234"  # ❌ Не тільки цифри
}
```

### Mood валідація
```python
# Приклад: POST /api/v2/journal
{
  "mood": "happy"  # ✅ Валідний (один з: happy, calm, energetic, sad, anxious, angry, tired)
}
{
  "mood": "excited"  # ❌ Невалідне значення
}
```

---

## Міграція з v1 на v2

### Перевірте свої API запити:

1. **Email поля** - переконайтеся що валідні email адреси
2. **Номери карток** - тільки цифри, 13-19 символів
3. **Обробка помилок** - очікуйте `errors` об'єкт замість одного `message`
4. **Відповіді** - v2 додає `count` та обгортає дані в `data` поле

### Приклад міграції:

**v1 Response:**
```json
[
  {"id": 1, "name": "Product 1"},
  {"id": 2, "name": "Product 2"}
]
```

**v2 Response:**
```json
{
  "status": "success",
  "count": 2,
  "data": [
    {"id": 1, "name": "Product 1"},
    {"id": 2, "name": "Product 2"}
  ]
}
```

---

## Рекомендації

- **Для нових проєктів:** Використовуйте API v2
- **Для існуючих клієнтів:** v1 залишається доступним (backwards compatibility)
- **Production:** Додайте rate limiting та authentication tokens
- **Моніторинг:** Відстежуйте `code` поля в помилках для аналітики

---

**Дата оновлення:** 1 грудня 2025  
**Версія документації:** 3.0
