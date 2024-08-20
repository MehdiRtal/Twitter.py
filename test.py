from twitter_py import Twitter
import asyncio

async def main():
    async with Twitter() as twitter:
        await twitter.login("GoodErnest19206", "YnXzT6U2")
        print(twitter.session)


asyncio.run(main())
