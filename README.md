# DailyMood 3.0

**Студент:** Ярослав Кудрик  
**Група:** ІП-14

## 📋 Опис проєкту

DailyMood 3.0 — веб-застосунок для трекінгу настрою з магазином wellness-ресурсів, Premium підпискою та рекомендаціями активностей.

## 💾 ВАЖЛИВО: Збереження бази даних

**База даних зберігається** в папці `./data/dailymood.db` і **НЕ видаляється** при:
- ✅ Перезапуску контейнера
- ✅ Оновленні коду
- ✅ Зупинці Docker

**Детальна документація:** [DOCKER_GUIDE.md](DOCKER_GUIDE.md)

### 🛡️ Безпечні команди Docker

```bash
docker compose restart        # Перезапуск (дані зберігаються)
docker compose up --build     # Оновлення образу (дані зберігаються)
docker compose down           # Зупинка (дані зберігаються)
```

### ⚠️ НЕБЕЗПЕЧНО
```bash
docker compose down -v        # Видаляє volume з БАЗОЮ ДАНИХ!
```

### 📦 Резервне копіювання

```bash
# Створити бекап
python backup_database.py

# Відновити з бекапу
python backup_database.py restore

# Перевірити стан бази
python test_data_persistence.py
```

## 📁 Структура проєкту

```
DailyMood3.0/
├── app.py                  # Flask сервер з REST API
├── models.py               # SQLAlchemy моделі
├── schemas.py              # Marshmallow валідація
├── README.md               # Цей файл (звіт ЛР6)
├── lab-reports/            # Матеріали звітів (скріншоти)
├── templates/
│   ├── base.html           # Базовий шаблон з темами
│   ├── lab6_feedback.html  # Сторінка ЛР6 (клієнт до Feedback API)
│   ├── checkout.html       # Checkout та оплати
│   └── ...
├── static/
│   ├── style.css           # Глобальні стилі
│   └── ...
├── scripts/                # Ініціалізація БД, сидери
│   ├── init_db.py
│   └── seed_products.py
└── postman/                # Колекція для тестів API
    └── DailyMood_API.postman_collection.json
```

## 🔌 API Endpoints

### GET `/api/feedback`
Отримує список останніх 50 відгуків.

**Відповідь:**
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Great app!",
    "rating": 5,
    "created_at": "2025-12-03T18:30:00"
  }
]
```

### POST `/api/feedback`
Створює новий відгук.

**Тіло запиту:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "message": "Amazing experience!",
  "rating": 5
}
```

### DELETE `/api/feedback/:id` (Admin)
Видаляє відгук за ID (лише для адміністраторів).

---

### Додатково (з ЛР5)
- `GET /api/products` — список продуктів магазину
- `POST /api/orders` — створення замовлення
- `POST /api/payments` — створення платежу (методи: `card`, `online_banking`, `paypal`)
  - Для `card` потрібні: `card_number`, `card_holder`, `card_expiry`, `card_cvv`, `card_brand`
- `POST /api/journal` — створення запису настрою
  - `mood`: `happy|neutral|sad`
  - `activities`: масив рядків, наприклад `["exercise", "reading"]`

## 📸 Скріншоти

### Головна сторінка ЛР6
![lab6-main](lab-reports/screenshots/lab6-main.png)

### Порожній список
![lab6-empty](lab-reports/screenshots/lab6-empty.png)

### Додавання відгуку
![lab6-form](lab-reports/screenshots/lab6-form.png)

### Повідомлення про успіх
![lab6-success](lab-reports/screenshots/lab6-success.png)

### Список з даними
![lab6-list](lab-reports/screenshots/lab6-list.png)

### Темна тема
![lab6-dark](lab-reports/screenshots/lab6-dark.png)

## 🚀 Як запустити

1. Встановіть залежності:
```bash
pip install -r requirements.txt
```
2. Ініціалізуйте базу даних:
```bash
python scripts/init_db.py
```
3. Запустіть сервер:
```bash
python app.py
```
або
```bash
run.bat
```
4. Відкрийте сторінку ЛР6:
```
http://127.0.0.1:5000/lab6
```

## 🧪 Тестування API

### Через Postman
- Імпортуйте `postman/DailyMood_API.postman_collection.json`
- Використайте запити: GET/POST/DELETE `/api/feedback`

### Через curl
Отримати список:
```bash
curl http://127.0.0.1:5000/api/feedback
```
Додати відгук:
```bash
curl -X POST http://127.0.0.1:5000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "email": "test@example.com", "message": "Great app!", "rating": 5}'
```

## � Документація

### Для користувачів
- 📖 **[Посібник користувача](docs/USER_GUIDE.md)** - детальні інструкції по використанню
- 🎯 Як створювати записи настрою
- 🏆 Робота зі звичками та цілями
- 🛍️ Покупка Premium підписки
- 💡 Поради та best practices

### Для розробників
- 🏗️ **[Архітектура проєкту](ARCHITECTURE.md)** - технічна документація
- 🔌 **[API Testing](docs/API_TESTING.md)** - результати performance тестування
- 📊 Детальна статистика по 28 endpoints
- 🐛 Known issues та їх рішення
- ⚡ Рекомендації по оптимізації
- 🐳 **[Docker Guide](DOCKER_GUIDE.md)** - контейнеризація
- 🔄 **[API Versions](docs/API_VERSIONS.md)** - версіонування API

## 🔗 Посилання
- Репозиторій: https://github.com/Yarik-eng/DailyMood
- Postman колекція: `postman/DailyMood_API.postman_collection.json`
- Performance reports: `postman/DailyMood-API-performance-report-*.html`

## ✅ Висновки

### ЛР6 - REST API та клієнт
Реалізовано клієнт до REST API на чистому JavaScript, організовано взаємодію з бекендом для створення та перегляду відгуків, налаштовано валідацію та обробку помилок. Опановано роботу з Fetch API, адаптивною стилізацією та базовою документуванням ендпоінтів.

### ЛР8 - Контейнеризація
Успішно контейнеризовано застосунок за допомогою Docker та Docker Compose. Налаштовано persistent storage для бази даних, healthchecks, змінні середовища. Застосунок готовий до deployment у будь-якому середовищі з Docker.

### ЛР9 - Тестування та документація
**Виявлені та виправлені помилки:**
1. ✅ Продукти неактивні за замовчуванням - активовано через SQL
2. ✅ Activities відправлялись як string замість array - виправлено у Postman
3. ✅ JSON syntax errors у Postman collection - виправлено структуру
4. ✅ Відсутні test scripts для збереження IDs - додано для entryId, habitId, goalId
5. ✅ Premium аватар для free користувачів - змінено на безкоштовний

**Performance тестування:**
- 📊 64,285 запитів протестовано
- ✅ 99.24% success rate під навантаженням
- ⚡ 162ms середній час відповіді
- 🚀 105.82 req/s throughput
- ⚠️ Виявлена проблема: GET /api/orders повільний (978ms) - потребує оптимізації

**Документація та інфраструктура:**
- 📖 [User Guide](docs/USER_GUIDE.md) - посібник користувача (393 lines)
- 🔌 [API Testing](docs/API_TESTING.md) - результати тестування та виправлення
- 🏗️ [Production Deployment](docs/PRODUCTION_DEPLOYMENT.md) - повний гайд
- 📋 [Lab 9 Report](LAB9_REPORT.md) - детальний звіт про виконання
- 📊 [Production Status](PRODUCTION_STATUS.md) - статус preparation
- ✅ [Production Checklist](PRODUCTION_CHECKLIST.md) - чек-лист для deployment

**Production Infrastructure:**
- 🐳 `docker-compose.production.yml` - PostgreSQL, Redis, Gunicorn, Nginx
- 📊 `docker-compose.monitoring.yml` - Prometheus, Grafana, AlertManager
- ⚙️ `gunicorn.conf.py` - WSGI server configuration
- 🔒 `nginx.conf` - Reverse proxy з SSL/TLS та security headers
- 🚀 `deploy_production.sh` - Bash deployment script
- 💻 `deploy_production.ps1` - PowerShell deployment script
- 🔄 `scripts/migrate_to_postgres.py` - Database migration

Застосунок повністю протестований, задокументований та готовий до production deployment.

## 🐳 Контейнеризація (ЛР8)

### Швидкий старт через Docker Compose

**Development:**
```bash
docker compose up --build
```

**Production:**
```bash
# 1. Налаштувати змінні середовища
cp .env.production .env
nano .env  # Змінити SECRET_KEY, паролі БД

# 2. Запустити production stack
docker compose -f docker-compose.production.yml up -d

# 3. Мігрувати дані (якщо потрібно)
python scripts/migrate_to_postgres.py
```

**Monitoring (опціонально):**
```bash
# Запустити Prometheus, Grafana, AlertManager
docker compose -f docker-compose.monitoring.yml up -d

# Відкрити:
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

- `http://127.0.0.1:5000` — застосунок (development)
- `https://yourdomain.com` — production з HTTPS через nginx

📖 **Детальна інструкція:** 
- [Production Deployment Guide](docs/PRODUCTION_DEPLOYMENT.md)
- [Production Checklist](PRODUCTION_CHECKLIST.md)

### Змінні середовища (.env)
Приклад у `.env.example`:
```
FLASK_ENV=production
SECRET_KEY=change-me
DATABASE_URL=sqlite:///data/dailymood.db
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000
```

### Dockerfile (основне)
- Базовий образ: `python:3.11-slim`
- Веб-сервер: `gunicorn app:app -b 0.0.0.0:5000`
- Healthcheck: `GET /health` (curl усередині контейнера)
- Оптимізація: `--no-cache-dir` для pip, slim образ, cleanup apt-lists

### Healthcheck endpoint
`/health` повертає `{ "status": "ok" }` для перевірок оркестратора.## 🎨 Особливості реалізації

- Vanilla JS у `lab6_feedback.html` з `async/await` та Fetch API
- Темізація через CSS variables, адаптивний дизайн
- Автоматичне оновлення списку після додавання відгуку
- Валідація на боці клієнта + на боці сервера (Marshmallow)

---

## 📋 Lab 9 - Кінцевий статус

✅ **3 з 4 завдань завершено:**
1. ✅ Виявлення та виправлення помилок (5+ bugs fixed, 64,285 requests tested)
2. ✅ Комплексна документація (10,000+ lines, українська мова)
3. ✅ Production deployment preparation (Docker, Nginx, PostgreSQL, monitoring)
4. ⏳ Презентаційні матеріали (гайд готовий: [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md))

**Головні файли Lab 9:**
- 📋 [LAB9_REPORT.md](LAB9_REPORT.md) - Детальний звіт про виконання
- 📊 [LAB9_SUMMARY.md](LAB9_SUMMARY.md) - Quick reference
- ✅ [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) - Чек-лист для deployment
- 🎤 [PRESENTATION_GUIDE.md](PRESENTATION_GUIDE.md) - Структура презентації

**Проєкт повністю готовий до production deployment! 🚀**