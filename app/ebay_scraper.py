from scraper_base import ScraperBase
from bs4 import BeautifulSoup as bs
import re

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