from scraper_base import ScraperBase
import re

class CraigslistScraper(ScraperBase):
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
            return []

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