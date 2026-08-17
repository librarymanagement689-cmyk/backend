import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('.env')

async def check():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client['library_management']
    books = await db['books'].find({}).to_list(200)
    q_books = [b for b in books if '?' in b.get('title', '') or '?' in (b.get('author') or '') or '?' in (b.get('category') or '')]
    print(f"Count of books with ? anywhere: {len(q_books)}")
    for b in q_books:
        print(f"ID: {b.get('book_id')} | title: {b.get('title')} | author: {b.get('author')} | cat: {b.get('category')} | part: {b.get('part_or_volume')} | series: {b.get('series_name')}")
    client.close()

if __name__ == '__main__':
    asyncio.run(check())
