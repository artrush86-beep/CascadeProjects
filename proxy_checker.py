import aiohttp
import asyncio
from typing import List, Dict, Optional
from geoip2.database import Reader
from geoip2.errors import AddressNotFoundError
import socket
from datetime import datetime


class ProxyChecker:
    """Проверка прокси на работоспособность и геолокацию"""
    
    def __init__(self, geoip_db_path: str = "GeoLite2-Country.mmdb"):
        self.geoip_reader = None
        try:
            self.geoip_reader = Reader(geoip_db_path)
        except Exception as e:
            print(f"Warning: Could not load GeoIP database: {e}")
    
    async def check_proxy(self, proxy: Dict, timeout: int = 10) -> Dict:
        """Проверка одного прокси"""
        result = {
            **proxy,
            'status': 'dead',
            'speed_ms': None,
            'country_code': proxy.get('country_code'),
            'anonymity': None,
            'error': None
        }
        
        proxy_url = self._format_proxy_url(proxy)
        
        try:
            start_time = datetime.utcnow()
            
            # Проверяем через httpbin.org/ip
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://httpbin.org/ip',
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    ssl=False
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        end_time = datetime.utcnow()
                        speed_ms = int((end_time - start_time).total_seconds() * 1000)
                        
                        result['status'] = 'active'
                        result['speed_ms'] = speed_ms
                        
                        # Определяем страну через GeoIP если не указана
                        if not result['country_code'] and self.geoip_reader:
                            try:
                                geoip_response = self.geoip_reader.country(proxy['ip'])
                                result['country_code'] = geoip_response.country.iso_code
                            except AddressNotFoundError:
                                pass
                        
                        # Проверяем anonymity (упрощенно)
                        result['anonymity'] = 'elite'  # Будет уточнено в полной версии
                        
        except asyncio.TimeoutError:
            result['error'] = 'timeout'
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def check_batch(self, proxies: List[Dict], batch_size: int = 100, timeout: int = 10) -> List[Dict]:
        """Параллельная проверка батча прокси"""
        results = []
        
        for i in range(0, len(proxies), batch_size):
            batch = proxies[i:i + batch_size]
            tasks = [self.check_proxy(proxy, timeout) for proxy in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, dict):
                    results.append(result)
                else:
                    print(f"Error in check: {result}")
        
        return results
    
    def _format_proxy_url(self, proxy: Dict) -> str:
        """Форматирование прокси для aiohttp"""
        if proxy.get('username') and proxy.get('password'):
            return f"http://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
        else:
            return f"http://{proxy['ip']}:{proxy['port']}"
    
    def is_country_restricted(self, country_code: str, exchange: str = "binance") -> bool:
        """Проверка на ограничения страны для биржи"""
        if not country_code:
            return True
        
        restricted_countries = {
            'binance': ['US', 'CA', 'CU', 'IR', 'KP', 'SY'],
            'okx': ['US', 'CA', 'IN', 'JP', 'MY', 'HK', 'CU', 'IR', 'KP', 'SY'],
            'bybit': ['US', 'GB', 'CA'],
            'bingx': ['CN', 'US']
        }
        
        return country_code.upper() in restricted_countries.get(exchange.lower(), [])
    
    def get_safe_countries(self) -> List[str]:
        """Список безопасных стран"""
        return [
            # Европа
            'DE', 'NL', 'FR', 'FI', 'PL', 'EE', 'SE', 'ES', 'IT', 'CZ', 
            'RO', 'BG', 'GR', 'PT', 'SK', 'SI', 'CH', 'TR', 'UA',
            # Азия
            'SG', 'TH', 'VN', 'ID', 'KZ', 'MN', 'PK', 'TW', 'KH', 'BD', 'LK',
            # Латинская Америка
            'BR', 'AR', 'CL', 'CO', 'MX', 'PE',
            # Другие
            'ZA'
        ]
