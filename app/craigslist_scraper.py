from scraper_base import ScraperBase
import re

class CraigslistScraper(ScraperBase):
    def __init__(self, location='chicago'):
        super().__init__()
        self.base_url = f"https://{location}.craigslist.org"
        self.api_url = "https://sapi.craigslist.org/web/v8/postings/search/full"

    async def search(self, query):
        await self._init_session()
        search_path = await self._perform_search(query)
        # testing error handling
        data = await self._api_request(query, search_path)
        return self._extract_listings(data) if data else []

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