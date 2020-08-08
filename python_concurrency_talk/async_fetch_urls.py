import asyncio
from typing import Dict, Set, Tuple

from fetch_urls import sites


async def fetch_site(url: str) -> Tuple[str, int, float]:
    """Return the size of a website and the time to load it."""
    import aiohttp
    from time import time
    start_time: float = time()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            page = await resp.read()
    duration: float = time() - start_time
    return url, len(page), duration


def get_result(tasks: Set[asyncio.Task]) -> Dict[str, Tuple[int, float]]:
    """Convert finished asyncio tasks to a dict."""
    result = {}
    for t in tasks:
        url, size, duration = t.result()
        result[url] = size, duration
    return result


def coroutine() -> Dict[str, Tuple[int, float]]:
    loop = asyncio.get_event_loop()
    tasks = []
    for url in sites:
        t = asyncio.ensure_future(fetch_site(url))
        tasks.append(t)
    done, _ = loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
    return get_result(done)


def coroutine2() -> Dict[str, Tuple[int, float]]:
    loop = asyncio.get_event_loop()
    done, _ = loop.run_until_complete(asyncio.wait(map(fetch_site, sites)))
    loop.close()
    return get_result(done)


def coroutine3() -> Dict[str, Tuple[int, float]]:
    done, _ = asyncio.run(asyncio.wait(map(fetch_site, sites)))
    return get_result(done)


if __name__ == '__main__':
    print(coroutine2())
