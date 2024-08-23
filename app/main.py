import asyncio
import zmq
import zmq.asyncio
import json
from craigslist_scraper import CraigslistScraper
from ebay_scraper import EbayScraper
from offerup_scraper import OfferUpScraper

class UsedItemsFinder:
    def __init__(self):
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.PUSH)
        self.zmq_socket.connect("tcp://host.containers.internal:5555")
        self.scrapers = [CraigslistScraper(), EbayScraper(), OfferUpScraper()]

    async def send_update(self, update):
        await self.zmq_socket.send_json(update)

    async def search(self, query):
        tasks = [scraper.search(query) for scraper in self.scrapers]
        results = await asyncio.gather(*tasks)
        for result_set in results:
            for item in result_set:
                await self.send_update(item)

    async def run(self):
        try:
            while True:
                command = await self.zmq_socket.recv_json()
                if command['type'] == 'search':
                    await self.search(command['query'])
        finally:
            for scraper in self.scrapers:
                await scraper.close()

if __name__ == "__main__":
    finder = UsedItemsFinder()
    asyncio.run(finder.run())