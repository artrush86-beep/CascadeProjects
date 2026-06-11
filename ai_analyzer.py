import asyncio
from typing import Optional, Dict, List
from config import settings
import google.generativeai as genai
from huggingface_hub import InferenceClient
import cohere


class AIAnalyzer:
    """AI анализатор для работы с прокси - поддерживает Gemini, HuggingFace, Cohere"""
    
    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self.model = settings.AI_MODEL
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Инициализация AI клиента"""
        if self.provider == "gemini" and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.client = genai.GenerativeModel(self.model)
        elif self.provider == "huggingface" and settings.HUGGINGFACE_API_KEY:
            self.client = InferenceClient(token=settings.HUGGINGFACE_API_KEY)
        elif self.provider == "cohere" and settings.COHERE_API_KEY:
            self.client = cohere.Client(settings.COHERE_API_KEY)
        else:
            print(f"AI provider {self.provider} not configured or missing API key")
    
    async def analyze_proxy_performance(self, proxies: List[Dict]) -> str:
        """Анализ производительности прокси"""
        if not self.client:
            return "AI не настроен. Добавьте API ключ в .env файл."
        
        # Подготовка данных для анализа
        active_count = sum(1 for p in proxies if p.get('status') == 'active')
        dead_count = sum(1 for p in proxies if p.get('status') == 'dead')
        countries = {}
        for p in proxies:
            country = p.get('country_code', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
        
        avg_speed = 0
        speeds = [p.get('speed_ms') for p in proxies if p.get('speed_ms')]
        if speeds:
            avg_speed = sum(speeds) // len(speeds)
        
        prompt = f"""
        Проанализируй следующие данные о прокси-серверах:
        
        Всего прокси: {len(proxies)}
        Активных: {active_count}
        Мертвых: {dead_count}
        Средняя скорость: {avg_speed} мс
        
        Распределение по странам:
        {', '.join([f'{k}: {v}' for k, v in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]])}
        
        Дай краткие рекомендации по оптимизации и какие страны показывают лучшие результаты.
        """
        
        try:
            if self.provider == "gemini":
                response = await asyncio.to_thread(self.client.generate_content, prompt)
                return response.text
            elif self.provider == "huggingface":
                response = await asyncio.to_thread(
                    self.client.text_generation,
                    prompt,
                    model=self.model or "mistralai/Mistral-7B-Instruct-v0.2"
                )
                return response[0]['generated_text'] if isinstance(response, list) else response
            elif self.provider == "cohere":
                response = await asyncio.to_thread(self.client.generate, prompt)
                return response.generations[0].text
        except Exception as e:
            return f"Ошибка AI анализа: {str(e)}"
        
        return "Анализ недоступен"
    
    async def recommend_proxies_for_exchange(self, exchange: str, region: str = "all") -> str:
        """Рекомендации по прокси для конкретной биржи"""
        if not self.client:
            return "AI не настроен. Добавьте API ключ в .env файл."
        
        exchange_restrictions = {
            'binance': 'Запрещены: US, CA, CU, IR, KP, SY. Частично: PH, TH, GB',
            'okx': 'Запрещены: US, CA, IN, JP, MY, HK. Частично: SG, GB, AU, BR, KR',
            'bybit': 'Запрещены: US, GB, CA',
            'bingx': 'Запрещены: CN, US'
        }
        
        prompt = f"""
        Мне нужны рекомендации по выбору прокси для биржи {exchange.upper()}.
        Ограничения биржи: {exchange_restrictions.get(exchange.lower(), 'Нет данных')}
        Желаемый регион: {region}
        
        Рекомендуй лучшие страны для прокси с учетом:
        1. Низкой задержки (ping)
        2. Отсутствия ограничений на бирже
        3. Стабильности соединения
        """
        
        try:
            if self.provider == "gemini":
                response = await asyncio.to_thread(self.client.generate_content, prompt)
                return response.text
            elif self.provider == "huggingface":
                response = await asyncio.to_thread(
                    self.client.text_generation,
                    prompt,
                    model=self.model or "mistralai/Mistral-7B-Instruct-v0.2"
                )
                return response[0]['generated_text'] if isinstance(response, list) else response
            elif self.provider == "cohere":
                response = await asyncio.to_thread(self.client.generate, prompt)
                return response.generations[0].text
        except Exception as e:
            return f"Ошибка AI рекомендаций: {str(e)}"
        
        return "Рекомендации недоступны"
    
    async def generate_report(self, data: Dict) -> str:
        """Генерация отчета на основе данных"""
        if not self.client:
            return "AI не настроен. Добавьте API ключ в .env файл."
        
        prompt = f"""
        Сгенерируй краткий отчет на основе следующих данных:
        {data}
        
        Формат: Markdown с заголовками и буллетами.
        """
        
        try:
            if self.provider == "gemini":
                response = await asyncio.to_thread(self.client.generate_content, prompt)
                return response.text
            elif self.provider == "huggingface":
                response = await asyncio.to_thread(
                    self.client.text_generation,
                    prompt,
                    model=self.model or "mistralai/Mistral-7B-Instruct-v0.2"
                )
                return response[0]['generated_text'] if isinstance(response, list) else response
            elif self.provider == "cohere":
                response = await asyncio.to_thread(self.client.generate, prompt)
                return response.generations[0].text
        except Exception as e:
            return f"Ошибка генерации отчета: {str(e)}"
        
        return "Отчет недоступен"
