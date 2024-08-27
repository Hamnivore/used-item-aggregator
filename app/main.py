from flask import Flask, render_template, jsonify
import asyncio
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from craigslist_scraper import CraigslistScraper
from ebay_scraper import EbayScraper
from offerup_scraper import OfferUpScraper

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class UsedItemsFinder:
    def __init__(self):
        self.scrapers = [CraigslistScraper(), EbayScraper(), OfferUpScraper()]
        self.results = {}
        self.active_searches = {}
        self.search_queue = Queue()
        self.loop = asyncio.new_event_loop()
        self.thread = None

    async def search(self, query, search_id):
        self.active_searches[search_id] = True
        try:
            tasks = [scraper.safe_search(query) for scraper in self.scrapers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            self.results[search_id] = []
            for scraper, result in zip(self.scrapers, results):
                if isinstance(result, Exception):
                    logging.error(f"Error in {scraper.__class__.__name__}: {str(result)}")
                    self.results[search_id].append({
                        "type": "error",
                        "source": scraper.__class__.__name__,
                        "message": f"Error: {str(result)}"
                    })
                elif result:
                    for item in result:
                        self.results[search_id].append({
                            "type": "result",
                            "source": scraper.__class__.__name__,
                            "data": item
                        })
                else:
                    logging.warning(f"{scraper.__class__.__name__} failed to return results")
        except Exception as e:
            logging.error(f"Error in search: {str(e)}")
        finally:
            self.active_searches[search_id] = False

    async def process_queue(self):
        while True:
            query, search_id = await self.loop.run_in_executor(None, self.search_queue.get)
            await self.search(query, search_id)
            self.search_queue.task_done()

    def start_background_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.create_task(self.process_queue())
        self.loop.run_forever()

    def start(self):
        if not self.thread:
            self.thread = ThreadPoolExecutor(max_workers=1).submit(self.start_background_loop)

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread:
            self.thread.result()

finder = UsedItemsFinder()
finder.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search/<query>')
def search(query):
    search_id = str(uuid.uuid4())
    finder.search_queue.put((query, search_id))
    return jsonify({"message": "Search queued", "search_id": search_id})

@app.route('/results/<search_id>')
def get_results(search_id):
    return jsonify({
        "is_searching": finder.active_searches.get(search_id, False),
        "results": finder.results.get(search_id, []),
        "search_id": search_id
    })

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
    finally:
        finder.stop()