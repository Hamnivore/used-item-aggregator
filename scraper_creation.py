import asyncio
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup as bs
import re
import sys
from abc import ABC, abstractmethod

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

class CraigslistScraper(ScraperBase):
    def __init__(self, location='chicago'):
        super().__init__()
        self.base_url = f"https://{location}.craigslist.org"
        self.api_url = "https://sapi.craigslist.org/web/v8/postings/search/full"

    async def search(self, query):
        await self._init_session()
        search_path = await self._perform_search(query)
        data = await self._api_request(query, search_path)
        return self._extract_listings(data) if data else None

    async def _init_session(self):
        response = await self.get(self.base_url, impersonate="chrome110")
        if response.status_code != 200:
            raise Exception(f"Failed to initialize session: {response.status_code}")

    async def _perform_search(self, query):
        search_url = f"{self.base_url}/search/sss?query={query}"
        response = await self.get(search_url, impersonate="chrome110")
        if response.status_code != 200:
            raise Exception(f"Failed to perform search: {response.status_code}")

        match = re.search(r'var searchPath = "([^"]+)";', response.text)
        return match.group(1) if match else "sss"

    async def _api_request(self, query, search_path):
        params = {
            'batch': '11-0-360-0-0',
            'cc': 'US',
            'lang': 'en',
            'query': query,
            'searchPath': search_path
        }

        headers = {
            'Accept': '*/*',
            'Origin': self.base_url,
            'Referer': self.base_url + '/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

        response = await self.get(
            self.api_url,
            params=params,
            headers=headers,
            impersonate="chrome110"
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: Status code {response.status_code}")
            return None

    def _extract_listings(self, data):
        listings = []
        items = data.get('data', {}).get('items', [])
        
        for item in items:
            listing = {
                'name': item[-1] if item else None,
                'price': item[3] if len(item) > 3 else None,
                'image_urls': [],
                'url': None
            }
            
            image_data = next((sublist for sublist in item if isinstance(sublist, list) and sublist and sublist[0] == 4), None)
            if image_data:
                listing['image_urls'] = self._construct_image_urls(image_data[1:])
            
            url_data = next((sublist for sublist in item if isinstance(sublist, list) and sublist and sublist[0] == 6), None)
            if url_data:
                listing['url'] = self._construct_item_url(url_data)
            
            listings.append(listing)
        return listings

    def _construct_item_url(self, url_data):
        url_part = url_data[1] if len(url_data) > 1 else ''
        return f"{self.base_url}/{url_part}.html"

    def _construct_image_urls(self, image_ids):
        base_image_url = "https://images.craigslist.org"
        return [f"{base_image_url}/{id.split(':')[1]}_300x300.jpg" for id in image_ids if ':' in id]

class EbayScraper(ScraperBase):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ebay.com/sch/i.html"

    async def search(self, query):
        params = {'_nkw': query}
        response = await self.get(self.base_url, params=params)
        
        if response.status_code == 200:
            return self._extract_listings(response.text)
        else:
            print(f"Error: Status code {response.status_code}")
            return None

    def _extract_listings(self, html):
        soup = bs(html, 'html.parser')
        listings = []

        ul = soup.select_one('.srp-results')
        if ul:
            for li in ul.find_all('li', id=True):
                listing = self._parse_listing(li)
                if listing:
                    listings.append(listing)

        return listings

    def _parse_listing(self, li):
        listing = {
            "name": None,
            "price": None,
            "image_urls": [],
            "url": None
        }

        title_elem = li.select_one('.s-item__title')
        if title_elem:
            listing["name"] = title_elem.text.strip()

        price_elem = li.select_one('.s-item__price')
        if price_elem:
            price_text = price_elem.text.strip()
            price_match = re.search(r'\$?([\d,]+(\.\d{2})?)', price_text)
            if price_match:
                listing["price"] = float(price_match.group(1).replace(',', ''))

        url_elem = li.select_one('a.s-item__link')
        if url_elem:
            listing["url"] = url_elem['href']

        img_elem = li.select_one('img')
        if img_elem:
            src = img_elem.get('src') or img_elem.get('data-src')
            if src:
                listing["image_urls"] = [src]

        return listing if listing["name"] else None

class OfferUpScraper(ScraperBase):
    def __init__(self):
        super().__init__()
        self.base_url = "https://offerup.com/search?q="

    async def search(self, query):
        response = await self.get(self.base_url + query)

        if response.status_code == 200:
            return self._extract_listings(response.text)
        else:
            print(f"Error: Status code {response.status_code}")
            return None
    
    def _extract_listings(self, html):
        soup = bs(html, 'html.parser')
        listings = []

        current_listings = soup.find('h2', string='Current listings')
        if current_listings:
            listings_container = current_listings.find_next('ul')
            
            if listings_container:
                for li in listings_container.find_all('li'):
                    listing = self._parse_listing(li)
                    if listing:
                        listings.append(listing)

        return listings

    def _parse_listing(self, li):
        listing = {
            "name": None,
            "price": None,
            "image_urls": [],
            "url": None
        }

        title_span = li.find('span', class_='MuiTypography-subtitle1')
        if title_span:
            listing["name"] = title_span.text.strip()

        price_span = li.find(string=re.compile(r'\$'))
        if price_span:
            price_match = re.search(r'\$?([\d,]+(\.\d{2})?)', price_span)
            if price_match:
                listing["price"] = float(price_match.group(1).replace(',', ''))

        a_tag = li.find('a')
        if a_tag and 'href' in a_tag.attrs:
            listing["url"] = "https://offerup.com" + a_tag['href']

        img_tag = li.find('img')
        if img_tag and 'src' in img_tag.attrs:
            listing["image_urls"] = [img_tag['src']]

        return listing if listing["name"] else None

async def main():
    scrapers = [CraigslistScraper(), EbayScraper(), OfferUpScraper()]
    search_query = "bike"

    tasks = [scraper.search(search_query) for scraper in scrapers]
    results = await asyncio.gather(*tasks)

    for scraper, result in zip(scrapers, results):
        print(f"Results from {scraper.__class__.__name__}:")
        if result:
            print(f"Successfully retrieved {len(result)} listings:")
            for item in result[:5]:  # Print first 5 items
                print(f"Name: {item['name']}")
                print(f"Price: ${item['price']}" if item['price'] else "Price: N/A")
                print(f"URL: {item['url']}")
                print("-" * 50)
        else:
            print("Failed to retrieve data")
        print("\n")

    # Close all sessions
    await asyncio.gather(*[scraper.close() for scraper in scrapers])

if __name__ == "__main__":
    import time
    start = time.perf_counter()
    asyncio.run(main())
    end = time.perf_counter()
    print(f"Finished in {end - start:.2f} second(s)")