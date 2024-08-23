import asyncio
from curl_cffi.requests import AsyncSession
from abc import ABC, abstractmethod
import sys

if sys.platform.startswith('win'):
    # Prevents a warning on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Common headers for all requests
common_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

class ScraperBase(ABC):
    def __init__(self):
        self.session = AsyncSession(headers=common_headers)
    
    @abstractmethod
    async def search(self, query):
        pass

    async def get(self, url, **kwargs):
        return await self.session.get(url, **kwargs)

    async def close(self):
        await self.session.close()