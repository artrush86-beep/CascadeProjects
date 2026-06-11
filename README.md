# 🤖 Proxy Agent Bot

Telegram-бот для поиска, проверки и анализа прокси-серверов для криптовалютных бирж с AI-аналитикой.

## ✨ Возможности

- 🔍 **Сбор бесплатных прокси** из множества источников (ProxyScrape, free-proxy-list.net)
- ✅ **Проверка работоспособности** с определением скорости и геолокации
- 🌍 **Фильтрация по странам** (Европа, Азия, Латинская Америка)
- 🚫 **Учет ограничений бирж** (Binance, OKX, Bybit, BingX)
- 🤖 **AI-аналитика** (Gemini, HuggingFace, Cohere)
- 📊 **Автоматическая проверка** каждые 30 минут
- 🚫 **Черный список** мертвых прокси
- 📈 **Статистика и отчеты**

## 🚀 Быстрый старт

### Локальный запуск

1. **Клонируйте репозиторий**
```bash
git clone <your-repo-url>
cd proxy-agent-bot
```

2. **Установите зависимости**
```bash
pip install -r requirements.txt
```

3. **Скачайте GeoLite2 базу данных**
```bash
# Зарегистрируйтесь на MaxMind и скачайте GeoLite2-Country.mmdb
# https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
# Поместите файл в корень проекта
```

4. **Настройте переменные окружения**
```bash
cp .env.example .env
# Отредактируйте .env и добавьте свои ключи
```

5. **Запустите бота**
```bash
python main.py
```

### Развертывание на Railway

1. **Создайте новый проект на Railway**
```bash
railway init
railway up
```

2. **Добавьте переменные окружения в Railway**
- `TELEGRAM_BOT_TOKEN` — токен вашего Telegram бота (от @BotFather)
- `DATABASE_URL` — PostgreSQL URL (Railway создаст автоматически)
- `GEMINI_API_KEY` — ключ Google Gemini API (бесплатный tier)
- `AI_PROVIDER` — `gemini` (или `huggingface`, `cohere`)

3. **Разверните**
```bash
railway deploy
```

## 🔑 Получение API ключей

### Telegram Bot Token
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

### Gemini API (бесплатный)
1. Перейдите на https://makersuite.google.com/app/apikey
2. Создайте новый API ключ
3. Бесплатный tier: 60 запросов/минуту

### HuggingFace API (бесплатный)
1. Перейдите на https://huggingface.co/settings/tokens
2. Создайте новый токен
3. Бесплатный tier для Inference API

### Cohere API (бесплатный)
1. Перейдите на https://dashboard.cohere.com/api-keys
2. Создайте новый API ключ
3. Бесплатный tier: 1000 вызовов/месяц

## 📋 Команды бота

| Команда | Описание | Пример |
|---------|----------|--------|
| `/start` | Главное меню | `/start` |
| `/help` | Справка | `/help` |
| `/scrape` | Собрать новые прокси | `/scrape` |
| `/get [биржа] [кол-во] [регион]` | Получить прокси для биржи | `/get binance 5 europe` |
| `/check [ip:port]` | Проверить прокси | `/check 8.211.49.86:87` |
| `/stats` | Статистика базы | `/stats` |
| `/analyze` | AI анализ прокси | `/analyze` |
| `/recommend [биржа]` | AI рекомендации | `/recommend okx` |

### Поддерживаемые биржи
- Binance
- OKX
- Bybit
- BingX

### Регионы
- `europe` — Европа
- `asia` — Азия
- `latam` — Латинская Америка
- `all` — Все регионы

## 🗄️ Структура базы данных

```
proxies          — Таблица прокси
blacklist        — Черный список мертвых прокси
exchange_rules   — Правила ограничений бирж
users            — Пользователи бота
check_history    — История проверок
```

## ⚙️ Конфигурация

### .env файл

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database (Railway PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@localhost/proxydb

# AI Services (выберите один)
GEMINI_API_KEY=your_gemini_key
# или
HUGGINGFACE_API_KEY=your_hf_key
# или
COHERE_API_KEY=your_cohere_key

# AI Settings
AI_PROVIDER=gemini
AI_MODEL=gemini-pro

# Proxy Settings
PROXY_CHECK_TIMEOUT=10
PROXY_CHECK_BATCH_SIZE=100
PROXY_AUTO_CHECK_INTERVAL=30

# GeoIP
GEOLITE2_DB_PATH=GeoLite2-Country.mmdb

# Scheduler
ENABLE_AUTO_CHECK=true
```

## 🔧 Автоматизация

### Автоматическая проверка прокси
- **Интервал**: каждые 30 минут
- **Правило**: 3 неудачные проверки → черный список
- **Очистка**: удаление из blacklist через 30 дней

### Cron-задачи
```
0 */30 * * *  — Проверка активных прокси
0 0 * * 1     — Очистка черного списка (каждый понедельник)
```

## 🌍 Безопасные страны

### Европа
DE, NL, FR, FI, PL, EE, SE, ES, IT, CZ, RO, BG, GR, PT, SK, SI, CH, TR, UA

### Азия
SG, TH, VN, ID, KZ, MN, PK, TW, KH, BD, LK

### Латинская Америка
BR, AR, CL, CO, MX, PE

### Другие
ZA (ЮАР)

## ⚠️ Ограничения бирж

### Binance
❌ Заблокировано: US, CA, CU, IR, KP, SY
⚠️ Частично: PH, TH, GB, NL

### OKX
❌ Заблокировано: US, CA, IN, JP, MY, HK, CU, IR, KP, SY
⚠️ Частично: SG, GB, AU, BR, KR

### Bybit
❌ Заблокировано: US, GB, CA

### BingX
❌ Заблокировано: CN, US

## 💰 Стоимость

| Сервис | Стоимость |
|--------|-----------|
| Railway Hobby | $5/мес |
| Telegram Bot | Бесплатно |
| GeoLite2 DB | Бесплатно |
| Gemini API | Бесплатный tier |
| HuggingFace | Бесплатный tier |
| Cohere API | Бесплатный tier |

**Итого**: $5/мес (только хостинг)

## 🛠️ Технологический стек

- **Bot Framework**: aiogram 3.x
- **HTTP Client**: aiohttp + aiohttp-socks
- **Database**: PostgreSQL + SQLAlchemy 2.0
- **Scheduler**: APScheduler
- **GeoIP**: geoip2 + GeoLite2
- **AI**: Gemini / HuggingFace / Cohere
- **Deployment**: Railway

## 📝 Лицензия

MIT License

## 🤝 Вклад

Pull requests приветствуются!

## 📞 Поддержка

По вопросам обращайтесь в Telegram: @your_username
