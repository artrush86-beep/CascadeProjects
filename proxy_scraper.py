import aiohttp
import asyncio
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
from datetime import datetime


class ProxyScraper:
    """Сборщик бесплатных прокси из различных источников"""
    
    def __init__(self):
        self.sources = [
            "https://api.proxyscrape.com/v4/free-proxy-list/get?request=getproxies&protocol=http&timeout=10000&country=all",
            "https://api.proxyscrape.com/v4/free-proxy-list/get?request=getproxies&protocol=socks4&timeout=10000&country=all",
            "https://api.proxyscrape.com/v4/free-proxy-list/get?request=getproxies&protocol=socks5&timeout=10000&country=all",
            "https://free-proxy-list.net/",
            "https://www.sslproxies.org/",
            "https://us-proxy.org/",
        ]
    
    async def fetch_proxyscrape(self, url: str) -> List[Dict]:
        """Получение прокси из ProxyScrape API"""
        proxies = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        text = await response.text()
                        lines = text.strip().split('\n')
                        for line in lines:
                            if ':' in line:
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    ip, port = parts[0], parts[1]
                                    protocol = 'socks5' if 'socks5' in url else ('socks4' if 'socks4' in url else 'http')
                                    proxies.append({
                                        'ip': ip,
                                        'port': int(port),
                                        'protocol': protocol,
                                        'source': 'proxyscrape',
                                        'username': None,
                                        'password': None
                                    })
        except Exception as e:
            print(f"Error fetching proxyscrape: {e}")
        return proxies
    
    async def fetch_freeproxylist(self, url: str) -> List[Dict]:
        """Парсинг free-proxy-list.net"""
        proxies = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        text = await response.text()
                        soup = BeautifulSoup(text, 'lxml')
                        table = soup.find('table', {'id': 'proxylisttable'})
                        if table:
                            rows = table.find_all('tr')[1:]  # Skip header
                            for row in rows:
                                cols = row.find_all('td')
                                if len(cols) >= 2:
                                    ip = cols[0].text.strip()
                                    port = cols[1].text.strip()
                                    country_code = cols[2].text.strip()[:2].upper() if len(cols) > 2 else None
                                    protocol = 'https' if 'ssl' in url else 'http'
                                    proxies.append({
                                        'ip': ip,
                                        'port': int(port),
                                        'protocol': protocol,
                                        'country_code': country_code,
                                        'source': 'freeproxylist',
                                        'username': None,
                                        'password': None
                                    })
        except Exception as e:
            print(f"Error fetching freeproxylist: {e}")
        return proxies
    
    async def scrape_all(self) -> List[Dict]:
        """Сбор прокси из всех источников"""
        all_proxies = []
        tasks = []
        
        for source in self.sources:
            if 'proxyscrape' in source:
                tasks.append(self.fetch_proxyscrape(source))
            else:
                tasks.append(self.fetch_freeproxylist(source))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_proxies.extend(result)
        
        # Убираем дубликаты
        unique_proxies = {}
        for proxy in all_proxies:
            key = f"{proxy['ip']}:{proxy['port']}:{proxy['protocol']}"
            if key not in unique_proxies:
                unique_proxies[key] = proxy
        
        return list(unique_proxies.values())
    
    def format_proxy(self, proxy: Dict, format_type: str = "full") -> str:
        """Форматирование прокси в нужный формат"""
        if format_type == "full":
            if proxy.get('username') and proxy.get('password'):
                return f"{proxy['protocol']}:{proxy['ip']}:{proxy['port']}:{proxy['username']}:{proxy['password']}"
            else:
                return f"{proxy['protocol']}://{proxy['ip']}:{proxy['port']}"
        elif format_type == "ip_port":
            return f"{proxy['ip']}:{proxy['port']}"
        elif format_type == "url":
            if proxy.get('username') and proxy.get('password'):
                return f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
            else:
                return f"{proxy['protocol']}://{proxy['ip']}:{proxy['port']}"
        else:
            return str(proxy)
