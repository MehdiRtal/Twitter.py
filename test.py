from twitter_py import Twitter

import asyncio

async def main():
    while True:
        try:
            async with Twitter() as twitter:
                await twitter.login("liu_madely4379", "Y2gqNHENu5")
                print(twitter.session)
        except Exception as e:
            print(e)

asyncio.run(main())
