from scraper_base import ScraperBase
from bs4 import BeautifulSoup as bs
import re

class OfferUpScraper(ScraperBase):
    def __init__(self):
        super().__init__()
        self.base_url = "https://offerup.com/search?q="

    async def search(self, session, query):
        response = await session.get(self.base_url + query)

        if response.status_code == 200:
            return self.extract_listings(response.text)
        else:
            print(f"Error: Status code {response.status_code}")
            return []
    
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

