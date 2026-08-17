import asyncio, os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('.env')

async def check():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client['library_management']
    books = await db['books'].find({}, {'book_id': 1, 'title': 1, 'language': 1, 'part_or_volume': 1, 'series_name': 1}).sort('book_id', 1).to_list(100)
    
    ok_count = 0
    bad_count = 0
    for b in books:
        title = b.get('title', '')
        has_q = '?' in title
        lang = b.get('language', '')
        if has_q:
            bad_count += 1
        else:
            ok_count += 1
        print(b.get('book_id'), '|', lang, '| bad=', has_q, '|', title[:50])
    
    print()
    print('Total books:', len(books))
    print('OK (no question marks):', ok_count)
    print('BAD (has question marks):', bad_count)
    client.close()

asyncio.run(check())
