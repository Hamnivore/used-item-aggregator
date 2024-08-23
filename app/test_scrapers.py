import asyncio
from craigslist_scraper import CraigslistScraper
from ebay_scraper import EbayScraper
from offerup_scraper import OfferUpScraper

async def test_scraper(scraper, query):
    print(f"\nTesting {scraper.__class__.__name__}...")
    try:
        results = await scraper.search(query)
        if results:
            print(f"Found {len(results)} results:")
            for item in results:
                print(f"- {item['title']}")
                print(f"  Price: {item['price']}")
                print(f"  Link: {item['link']}")
                print(f"  Source: {item['source']}")
                print()
        else:
            print("No results found.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        await scraper.close()

async def main():
    query = "vintage camera"
    scrapers = [CraigslistScraper(), EbayScraper(), OfferUpScraper()]
    
    tasks = [test_scraper(scraper, query) for scraper in scrapers]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())