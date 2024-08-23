import asyncio
from curl_cffi.requests import AsyncSession
from curl_cffi import requests
from bs4 import BeautifulSoup as bs
import re
import sys

if sys.platform.startswith('win'):
    # stops a warning from being thrown if you're on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class AsyncScraper:
    def __init__(self):
        self.headers = {
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

    async def search(self, session, query):
        raise NotImplementedError("Subclasses must implement this method")

# %%
class AsyncCraigslistScraper(AsyncScraper):
    """
    Output Format:
    The function returns a list of dictionaries, where each dictionary represents a Craigslist listing.
    Each dictionary has the following structure:

    [
        {
            "name": "Item Title",
            "price": 100,  # Numeric price, or None if not available
            "image_urls": [  # List of image URLs, or empty list if no images
                "https://images.craigslist.org/00A0A_example1_300x300.jpg",
                "https://images.craigslist.org/00B0B_example2_300x300.jpg"
            ],
            "url": "https://chicago.craigslist.org/example-item-url.html"  # Full item URL, or None if not available
        },
        {
            "name": "Another Item",
            "price": 50,
            "image_urls": [],  # Empty if no images
            "url": "https://chicago.craigslist.org/another-item-url.html"
        },
        # ... more listings ...
    ]

    Note: Any of these fields (except 'name') might be None or an empty list if the data is not available in the original listing.
    """
    def __init__(self, location='chicago'):
        super().__init__()
        self.base_url = f"https://{location}.craigslist.org"
        self.api_url = "https://sapi.craigslist.org/web/v8/postings/search/full"

    async def search(self, session, query):
        await self.init_session(session)
        search_path = await self.perform_search(session, query)
        data = await self.api_request(session, query, search_path)
        if data:
            return self.extract_listings(data)
        else:
            return None

    async def init_session(self, session):
        response = await session.get(self.base_url, impersonate="chrome110")
        if response.status_code != 200:
            raise Exception(f"Failed to initialize session: {response.status_code}")

    async def perform_search(self, session, query):
        search_url = f"{self.base_url}/search/sss?query={query}"
        response = await session.get(search_url, impersonate="chrome110")
        if response.status_code != 200:
            raise Exception(f"Failed to perform search: {response.status_code}")

        match = re.search(r'var searchPath = "([^"]+)";', response.text)
        return match.group(1) if match else "sss"

    async def api_request(self, session, query, search_path):
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

        response = await session.get(
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

    def extract_listings(self, data):
        listings = []
        items = data.get('data', {}).get('items', [])
        
        for item in items:
            listing = {}
            listing['name'] = item[-1] if item else None
            listing['price'] = item[3] if len(item) > 3 else None
            
            image_data = next((sublist for sublist in item if isinstance(sublist, list) and sublist and sublist[0] == 4), None)
            if image_data:
                listing['image_urls'] = self.construct_image_urls(image_data[1:])
            else:
                listing['image_urls'] = []
            
            url_data = next((sublist for sublist in item if isinstance(sublist, list) and sublist and sublist[0] == 6), None)
            if url_data:
                listing['url'] = self.construct_item_url(url_data)
            else:
                listing['url'] = None
            
            listings.append(listing)
        return listings

    def construct_item_url(self, url_data):
        url_part = url_data[1] if len(url_data) > 1 else ''
        return f"{self.base_url}/{url_part}.html"

    def construct_image_urls(self, image_ids):
        base_image_url = "https://images.craigslist.org"
        return [f"{base_image_url}/{id.split(':')[1]}_300x300.jpg" for id in image_ids if ':' in id]

# %%
class AsyncEbayScraper(AsyncScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.ebay.com/sch/i.html"

    async def search(self, session, query):
        params = {'_nkw': query}
        response = await session.get(self.base_url, params=params)
        
        if response.status_code == 200:
            return self.extract_listings(response.text)
        else:
            print(f"Error: Status code {response.status_code}")
            return None

    def extract_listings(self, html):
        soup = bs(html, 'html.parser')
        listings = []

        # Find the unordered list with class 'srp-results'
        ul = soup.select_one('.srp-results')
        if ul:
            # Find all list items with an id attribute
            for li in ul.find_all('li', id=True):
                listing = self.parse_listing(li)
                if listing:
                    listings.append(listing)

        return listings

    def parse_listing(self, li):
        listing = {
            "name": None,
            "price": None,
            "image_urls": [],
            "url": None
        }

        # Extract title
        title_elem = li.select_one('.s-item__title')
        if title_elem:
            listing["name"] = title_elem.text.strip()

        # Extract price
        price_elem = li.select_one('.s-item__price')
        if price_elem:
            price_text = price_elem.text.strip()
            price_match = re.search(r'\$?([\d,]+(\.\d{2})?)', price_text)
            if price_match:
                listing["price"] = float(price_match.group(1).replace(',', ''))

        # Extract URL
        url_elem = li.select_one('a.s-item__link')
        if url_elem:
            listing["url"] = url_elem['href']

        # Extract image URL (just the first img element)
        img_elem = li.select_one('img')
        if img_elem:
            src = img_elem.get('src') or img_elem.get('data-src')
            if src:
                listing["image_urls"] = [src]

        return listing if listing["name"] else None

# %%
class AsyncOfferUpScraper(AsyncScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://offerup.com/search?q="

    async def search(self, session, query):
        response = await session.get(self.base_url + query)

        if response.status_code == 200:
            return self.extract_listings(response.text)
        else:
            print(f"Error: Status code {response.status_code}")
            return None
    
    def extract_listings(self, html):
        soup = bs(html, 'html.parser')
        listings = []

        # Find the "Current listings" section
        current_listings = soup.find('h2', string='Current listings')
        if current_listings:
            # Find the closest container that might hold the listings
            listings_container = current_listings.find_next('ul')
            
            if listings_container:
                for li in listings_container.find_all('li'):
                    listing = self.parse_listing(li)
                    if listing:
                        listings.append(listing)

        return listings

    def parse_listing(self, li):
        listing = {
            "name": None,
            "price": None,
            "image_urls": [],
            "url": None
        }

        # Extract title (first span with MuiTypography-subtitle1 class)
        title_span = li.find('span', class_='MuiTypography-subtitle1')
        if title_span:
            listing["name"] = title_span.text.strip()

        # Extract price (look for $ sign)
        price_span = li.find(string=re.compile(r'\$'))
        if price_span:
            price_match = re.search(r'\$?([\d,]+(\.\d{2})?)', price_span)
            if price_match:
                listing["price"] = float(price_match.group(1).replace(',', ''))

        # Extract URL
        a_tag = li.find('a')
        if a_tag and 'href' in a_tag.attrs:
            listing["url"] = "https://offerup.com" + a_tag['href']

        # Extract image URL
        img_tag = li.find('img')
        if img_tag and 'src' in img_tag.attrs:
            listing["image_urls"] = [img_tag['src']]

        return listing if listing["name"] else None

# %%
async def main():
    scrapers = [AsyncCraigslistScraper(), AsyncEbayScraper(), AsyncOfferUpScraper()]
    search_query = "bike"

    async with AsyncSession(headers=AsyncScraper().headers) as session:
        tasks = [scraper.search(session, search_query) for scraper in scrapers]
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

if __name__ == "__main__":
    asyncio.run(main())


