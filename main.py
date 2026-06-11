import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

from config import settings
from database import init_db, async_session, Proxy, Blacklist
from proxy_checker import ProxyChecker
from bot import ProxyBot

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxyAgent:
    def __init__(self):
        self.bot = ProxyBot()
        self.checker = ProxyChecker(settings.GEOLITE2_DB_PATH)
        self.scheduler = AsyncIOScheduler()
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Настройка планировщика задач"""
        if settings.ENABLE_AUTO_CHECK:
            # Проверка прокси каждые 30 минут
            self.scheduler.add_job(
                self.auto_check_proxies,
                trigger=IntervalTrigger(minutes=settings.PROXY_AUTO_CHECK_INTERVAL),
                id='auto_check_proxies',
                name='Auto check proxies',
                replace_existing=True
            )
            
            # Очистка черного списка раз в неделю
            self.scheduler.add_job(
                self.cleanup_blacklist,
                trigger='cron',
                day_of_week='mon',
                hour=0,
                minute=0,
                id='cleanup_blacklist',
                name='Cleanup blacklist',
                replace_existing=True
            )
    
    async def auto_check_proxies(self):
        """Автоматическая проверка активных прокси"""
        logger.info("Starting auto check of proxies...")
        
        async with async_session() as session:
            from sqlalchemy import select
            
            # Получаем активные прокси
            result = await session.execute(
                select(Proxy).where(Proxy.status == 'active')
            )
            proxies = result.scalars().all()
            
            if not proxies:
                logger.info("No active proxies to check")
                return
            
            # Конвертируем в словари для проверки
            proxy_dicts = []
            for p in proxies:
                proxy_dicts.append({
                    'ip': p.ip,
                    'port': p.port,
                    'protocol': p.protocol,
                    'country_code': p.country_code,
                    'username': p.username,
                    'password': p.password
                })
            
            # Проверяем батчами
            batch_size = settings.PROXY_CHECK_BATCH_SIZE
            checked_count = 0
            moved_to_blacklist = 0
            
            for i in range(0, len(proxy_dicts), batch_size):
                batch = proxy_dicts[i:i + batch_size]
                results = await self.checker.check_batch(
                    batch,
                    batch_size=batch_size,
                    timeout=settings.PROXY_CHECK_TIMEOUT
                )
                
                for proxy_obj, result in zip(proxies[i:i + batch_size], results):
                    checked_count += 1
                    
                    if result['status'] == 'active':
                        # Сбрасываем счетчик неудач
                        proxy_obj.fail_count = 0
                        proxy_obj.last_check = datetime.utcnow()
                        proxy_obj.speed_ms = result.get('speed_ms')
                        if result.get('country_code'):
                            proxy_obj.country_code = result['country_code']
                    else:
                        # Увеличиваем счетчик неудач
                        proxy_obj.fail_count += 1
                        proxy_obj.last_check = datetime.utcnow()
                        
                        # Если 3 неудачи - в черный список
                        if proxy_obj.fail_count >= 3:
                            # Добавляем в черный список
                            blacklist_entry = Blacklist(
                                ip=proxy_obj.ip,
                                port=proxy_obj.port,
                                reason='3_failures',
                                source='auto_check'
                            )
                            session.add(blacklist_entry)
                            
                            # Удаляем из активных
                            proxy_obj.status = 'dead'
                            moved_to_blacklist += 1
                            logger.info(f"Moved {proxy_obj.ip}:{proxy_obj.port} to blacklist")
                
                await session.commit()
                logger.info(f"Checked batch {i//batch_size + 1}/{(len(proxy_dicts) + batch_size - 1)//batch_size}")
            
            logger.info(f"Auto check completed: {checked_count} proxies checked, {moved_to_blacklist} moved to blacklist")
    
    async def cleanup_blacklist(self):
        """Очистка старых записей из черного списка"""
        logger.info("Cleaning up old blacklist entries...")
        
        async with async_session() as session:
            from sqlalchemy import delete
            from datetime import timedelta
            
            # Удаляем записи старше 30 дней
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            stmt = delete(Blacklist).where(Blacklist.added_at < cutoff_date)
            result = await session.execute(stmt)
            deleted_count = result.rowcount
            
            await session.commit()
            
            logger.info(f"Cleanup completed: {deleted_count} old entries removed from blacklist")
    
    async def start(self):
        """Запуск агента"""
        logger.info("Initializing database...")
        await init_db()
        
        logger.info("Starting scheduler...")
        self.scheduler.start()
        
        logger.info("Starting bot...")
        await self.bot.start()


if __name__ == "__main__":
    agent = ProxyAgent()
    asyncio.run(agent.start())
