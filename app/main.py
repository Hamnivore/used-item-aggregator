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
        self.zmq_socket = self.zmq_context.socket(zmq.PAIR)
        self.zmq_socket.bind("tcp://*:5555")
        self.scrapers = [CraigslistScraper(), EbayScraper(), OfferUpScraper()]

    async def send_update(self, update):
        await self.zmq_socket.send_json(update)

    async def search(self, query):
        tasks = [scraper.search(query) for scraper in self.scrapers]
        results = await asyncio.gather(*tasks)
        for scraper, result in zip(self.scrapers, results):
            if result:
                for item in result:
                    await self.send_update({
                        "type": "result",
                        "source": scraper.__class__.__name__,
                        "data": item
                    })
        await self.send_update({"type": "search_complete"})

    async def run(self):
        print("UsedItemsFinder is running and waiting for commands...")
        try:
            while True:
                message = await self.zmq_socket.recv_json()
                if message['type'] == 'search':
                    print(f"Received search request for: {message['query']}")
                    await self.search(message['query'])
                elif message['type'] == 'exit':
                    print("Received exit command. Shutting down...")
                    break
        finally:
            for scraper in self.scrapers:
                await scraper.close()

async def main():
    finder = UsedItemsFinder()
    await finder.run()

if __name__ == "__main__":
    asyncio.run(main())