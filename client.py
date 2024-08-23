import asyncio
import zmq
import zmq.asyncio
import json

class UsedItemsFinderClient:
    def __init__(self):
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.PAIR)
        self.zmq_socket.connect("tcp://localhost:5555")

    async def send_command(self, command):
        await self.zmq_socket.send_json(command)

    async def receive_results(self):
        while True:
            message = await self.zmq_socket.recv_json()
            if message['type'] == 'result':
                print(f"Received from {message['source']}:")
                print(f"Name: {message['data']['name']}")
                print(f"Price: ${message['data']['price']}" if message['data']['price'] else "Price: N/A")
                print(f"URL: {message['data']['url']}")
                print("-" * 50)
            elif message['type'] == 'search_complete':
                print("Search completed.")
                break

    async def run(self):
        while True:
            command = input("Enter a command (search <query> or exit): ").split(maxsplit=1)
            if command[0] == 'search' and len(command) > 1:
                await self.send_command({"type": "search", "query": command[1]})
                await self.receive_results()
            elif command[0] == 'exit':
                await self.send_command({"type": "exit"})
                break
            else:
                print("Invalid command. Use 'search <query>' or 'exit'.")

async def main():
    client = UsedItemsFinderClient()
    await client.run()

if __name__ == "__main__":
    asyncio.run(main())