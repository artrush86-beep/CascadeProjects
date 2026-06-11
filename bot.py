from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import asyncio
from typing import Optional

from config import settings
from database import async_session, Proxy, Blacklist, User
from proxy_scraper import ProxyScraper
from proxy_checker import ProxyChecker
from ai_analyzer import AIAnalyzer


class ProxyStates(StatesGroup):
    waiting_for_exchange = State()
    waiting_for_count = State()
    waiting_for_region = State()
    waiting_for_check = State()


class ProxyBot:
    def __init__(self):
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        self.scraper = ProxyScraper()
        self.checker = ProxyChecker(settings.GEOLITE2_DB_PATH)
        self.ai = AIAnalyzer()
        self._setup_handlers()
    
    def _setup_handlers(self):
        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(Command("help"))(self.cmd_help)
        self.dp.message(Command("get"))(self.cmd_get)
        self.dp.message(Command("check"))(self.cmd_check)
        self.dp.message(Command("stats"))(self.cmd_stats)
        self.dp.message(Command("analyze"))(self.cmd_analyze)
        self.dp.message(Command("recommend"))(self.cmd_recommend)
        self.dp.message(Command("scrape"))(self.cmd_scrape)
        self.dp.callback_query(F.data.startswith("exchange_"))(self.callback_exchange)
        self.dp.callback_query(F.data.startswith("region_"))(self.callback_region)
    
    async def cmd_start(self, message: types.Message):
        """Команда /start"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти прокси", callback_data="scrape")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="🤖 AI Анализ", callback_data="analyze")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
        ])
        
        await message.answer(
            "🤖 *Proxy Agent Bot*\n\n"
            "Бот для поиска и проверки прокси-серверов для криптовалютных бирж.\n\n"
            "Доступные команды:\n"
            "/get - Получить прокси для биржи\n"
            "/check - Проверить прокси\n"
            "/scrape - Собрать новые прокси\n"
            "/stats - Статистика базы\n"
            "/analyze - AI анализ\n"
            "/recommend - Рекомендации AI",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    async def cmd_help(self, message: types.Message):
        """Команда /help"""
        help_text = """
📖 *Справка*

Команды:
/start - Главное меню
/get [биржа] [кол-во] - Получить прокси
  Пример: /get binance 5
/check [ip:port] - Проверить прокси
/scrape - Собрать новые прокси
/stats - Статистика базы
/analyze - AI анализ прокси
/recommend [биржа] - Рекомендации AI

Поддерживаемые биржи:
• Binance
• OKX
• Bybit
• BingX

Регионы:
• europe - Европа
• asia - Азия
• latam - Латинская Америка
• all - Все регионы
        """
        await message.answer(help_text, parse_mode="Markdown")
    
    async def cmd_scrape(self, message: types.Message):
        """Сбор новых прокси"""
        await message.answer("🔍 Собираю прокси из источников... Это может занять время.")
        
        try:
            proxies = await self.scraper.scrape_all()
            
            if not proxies:
                await message.answer("❌ Не удалось собрать прокси")
                return
            
            # Сохраняем в базу
            async with async_session() as session:
                added_count = 0
                for proxy_data in proxies:
                    # Проверяем на дубликаты и blacklist
                    existing = await session.execute(
                        select(Proxy).where(
                            Proxy.ip == proxy_data['ip'],
                            Proxy.port == proxy_data['port'],
                            Proxy.protocol == proxy_data['protocol']
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue
                    
                    blacklisted = await session.execute(
                        select(Blacklist).where(
                            Blacklist.ip == proxy_data['ip'],
                            Blacklist.port == proxy_data['port']
                        )
                    )
                    if blacklisted.scalar_one_or_none():
                        continue
                    
                    new_proxy = Proxy(
                        ip=proxy_data['ip'],
                        port=proxy_data['port'],
                        protocol=proxy_data['protocol'],
                        country_code=proxy_data.get('country_code'),
                        source=proxy_data.get('source', 'unknown'),
                        username=proxy_data.get('username'),
                        password=proxy_data.get('password')
                    )
                    session.add(new_proxy)
                    added_count += 1
                
                await session.commit()
            
            await message.answer(f"✅ Собрано {len(proxies)} прокси, добавлено {added_count} новых")
            
        except Exception as e:
            await message.answer(f"❌ Ошибка: {str(e)}")
    
    async def cmd_get(self, message: types.Message, state: FSMContext):
        """Получить прокси для биржи"""
        args = message.text.split()
        
        if len(args) < 2:
            # Показываем выбор биржи
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Binance", callback_data="exchange_binance"),
                    InlineKeyboardButton(text="OKX", callback_data="exchange_okx")
                ],
                [
                    InlineKeyboardButton(text="Bybit", callback_data="exchange_bybit"),
                    InlineKeyboardButton(text="BingX", callback_data="exchange_bingx")
                ]
            ])
            await message.answer("Выберите биржу:", reply_markup=keyboard)
            await state.set_state(ProxyStates.waiting_for_exchange)
            return
        
        exchange = args[1].lower()
        count = int(args[2]) if len(args) > 2 else 5
        region = args[3].lower() if len(args) > 3 else "all"
        
        await self._get_proxies_for_exchange(message, exchange, count, region)
    
    async def callback_exchange(self, callback: types.CallbackQuery, state: FSMContext):
        """Обработка выбора биржи"""
        exchange = callback.data.split("_")[1]
        await state.update_data(exchange=exchange)
        
        # Показываем выбор региона
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌍 Все", callback_data="region_all"),
                InlineKeyboardButton(text="🇪🇺 Европа", callback_data="region_europe")
            ],
            [
                InlineKeyboardButton(text="🌏 Азия", callback_data="region_asia"),
                InlineKeyboardButton(text="🌎 ЛатАмерика", callback_data="region_latam")
            ]
        ])
        await callback.message.edit_text("Выберите регион:", reply_markup=keyboard)
        await state.set_state(ProxyStates.waiting_for_region)
        await callback.answer()
    
    async def callback_region(self, callback: types.CallbackQuery, state: FSMContext):
        """Обработка выбора региона"""
        region = callback.data.split("_")[1]
        data = await state.get_data()
        exchange = data.get('exchange', 'binance')
        
        # Спрашиваем количество
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="3", callback_data="count_3"),
                InlineKeyboardButton(text="5", callback_data="count_5"),
                InlineKeyboardButton(text="10", callback_data="count_10")
            ]
        ])
        await state.update_data(region=region)
        await callback.message.edit_text("Выберите количество:", reply_markup=keyboard)
        await state.set_state(ProxyStates.waiting_for_count)
        await callback.answer()
    
    async def _get_proxies_for_exchange(self, message: types.Message, exchange: str, count: int, region: str):
        """Получение прокси для биржи"""
        await message.answer(f"🔍 Ищу {count} прокси для {exchange.upper()} ({region})...")
        
        async with async_session() as session:
            # Фильтруем по стране
            safe_countries = self.checker.get_safe_countries()
            
            if region != "all":
                region_map = {
                    'europe': ['DE', 'NL', 'FR', 'FI', 'PL', 'EE', 'SE', 'ES', 'IT'],
                    'asia': ['SG', 'TH', 'VN', 'ID', 'KZ', 'MN', 'PK', 'TW'],
                    'latam': ['BR', 'AR', 'CL', 'CO', 'MX', 'PE']
                }
                safe_countries = region_map.get(region, safe_countries)
            
            # Получаем активные прокси
            from sqlalchemy import select
            query = select(Proxy).where(
                Proxy.status == 'active',
                Proxy.country_code.in_(safe_countries)
            ).limit(count * 2)  # Берем с запасом
            
            result = await session.execute(query)
            proxies = result.scalars().all()
            
            # Дополнительно фильтруем по ограничениям биржи
            filtered_proxies = []
            for proxy in proxies:
                if not self.checker.is_country_restricted(proxy.country_code, exchange):
                    filtered_proxies.append(proxy)
                if len(filtered_proxies) >= count:
                    break
            
            if not filtered_proxies:
                await message.answer("❌ Не найдено подходящих прокси. Попробуйте /scrape для сбора новых.")
                return
            
            # Форматируем вывод
            response = f"✅ Найдено {len(filtered_proxies)} прокси для {exchange.upper()}:\n\n"
            for proxy in filtered_proxies:
                if proxy.username and proxy.password:
                    response += f"{proxy.protocol}:{proxy.ip}:{proxy.port}:{proxy.username}:{proxy.password}\n"
                else:
                    response += f"{proxy.protocol}://{proxy.ip}:{proxy.port}\n"
                response += f"📍 {proxy.country_code} | ⚡ {proxy.speed_ms}ms\n\n"
            
            await message.answer(response)
    
    async def cmd_check(self, message: types.Message):
        """Проверить прокси"""
        args = message.text.split()
        
        if len(args) < 2:
            await message.answer("Использование: /check ip:port")
            return
        
        proxy_str = args[1]
        parts = proxy_str.split(':')
        
        if len(parts) < 2:
            await message.answer("Неверный формат. Используйте: /check ip:port")
            return
        
        proxy_data = {
            'ip': parts[0],
            'port': int(parts[1]),
            'protocol': 'http',
            'username': None,
            'password': None
        }
        
        await message.answer("🔍 Проверяю прокси...")
        
        result = await self.checker.check_proxy(proxy_data)
        
        if result['status'] == 'active':
            response = f"✅ Прокси работает\n\n"
            response += f"IP: {result['ip']}:{result['port']}\n"
            response += f"Страна: {result.get('country_code', 'Unknown')}\n"
            response += f"Скорость: {result.get('speed_ms', 'N/A')}ms\n"
            response += f"Anonymity: {result.get('anonymity', 'N/A')}"
        else:
            response = f"❌ Прокси не работает\n\n"
            response += f"Ошибка: {result.get('error', 'Unknown')}"
        
        await message.answer(response)
    
    async def cmd_stats(self, message: types.Message):
        """Статистика базы"""
        async with async_session() as session:
            from sqlalchemy import select, func
            
            total = await session.execute(select(func.count(Proxy.id)))
            total_count = total.scalar()
            
            active = await session.execute(
                select(func.count(Proxy.id)).where(Proxy.status == 'active')
            )
            active_count = active.scalar()
            
            dead = await session.execute(
                select(func.count(Proxy.id)).where(Proxy.status == 'dead')
            )
            dead_count = dead.scalar()
            
            blacklisted = await session.execute(select(func.count(Blacklist.id)))
            blacklisted_count = blacklisted.scalar()
            
            response = f"📊 *Статистика*\n\n"
            response += f"Всего прокси: {total_count}\n"
            response += f"✅ Активных: {active_count}\n"
            response += f"❌ Мертвых: {dead_count}\n"
            response += f"🚫 В черном списке: {blacklisted_count}"
            
            await message.answer(response, parse_mode="Markdown")
    
    async def cmd_analyze(self, message: types.Message):
        """AI анализ"""
        await message.answer("🤖 Анализирую базу прокси...")
        
        async with async_session() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(Proxy).where(Proxy.status == 'active').limit(50)
            )
            proxies = result.scalars().all()
            
            proxy_dicts = []
            for p in proxies:
                proxy_dicts.append({
                    'ip': p.ip,
                    'port': p.port,
                    'status': p.status,
                    'country_code': p.country_code,
                    'speed_ms': p.speed_ms
                })
            
            analysis = await self.ai.analyze_proxy_performance(proxy_dicts)
            await message.answer(f"🤖 *AI Анализ*\n\n{analysis}", parse_mode="Markdown")
    
    async def cmd_recommend(self, message: types.Message):
        """AI рекомендации"""
        args = message.text.split()
        exchange = args[1].lower() if len(args) > 1 else "binance"
        
        await message.answer(f"🤖 Генерирую рекомендации для {exchange.upper()}...")
        
        recommendation = await self.ai.recommend_proxies_for_exchange(exchange)
        await message.answer(f"🤖 *Рекомендации для {exchange.upper()}*\n\n{recommendation}", parse_mode="Markdown")
    
    async def start(self):
        """Запуск бота"""
        print("Bot started")
        await self.dp.start_polling(self.bot)


# Импорты для SQLAlchemy
from sqlalchemy import select
