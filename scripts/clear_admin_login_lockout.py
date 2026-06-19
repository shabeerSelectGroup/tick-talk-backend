"""Clear admin security-code rate limit in Redis. Run: PYTHONPATH=. python -m scripts.clear_admin_login_lockout"""

import asyncio

from app.core.redis import close_redis, get_redis

KEY = "admin_login_attempts:_admin_security_code"


async def main() -> None:
    redis = await get_redis()
    deleted = await redis.delete(KEY)
    print(f"Deleted {deleted} lockout key(s) for admin login.")
    await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
