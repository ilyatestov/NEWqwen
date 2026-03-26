import aiosqlite
import hashlib

DB = "seen_posts.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS seen (hash TEXT PRIMARY KEY)")
        await db.commit()

async def is_seen(link: str) -> bool:
    h = hashlib.md5(link.encode()).hexdigest()
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT 1 FROM seen WHERE hash=?", (h,)) as cursor:
            return await cursor.fetchone() is not None

async def mark_seen(link: str):
    h = hashlib.md5(link.encode()).hexdigest()
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO seen (hash) VALUES (?)", (h,))
        await db.commit()
