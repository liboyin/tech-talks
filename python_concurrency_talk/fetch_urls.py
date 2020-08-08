from typing import Dict, List, Tuple

sites: List[str] = [
    'https://www.python.org/',
    'https://pypi.org/',
    'https://conda.io/',
    'http://www.jython.org/',
    'http://ironpython.net/',
    'https://pypy.org/',
    'https://github.com/',
    'https://stackoverflow.com/',
]


def fetch_site(url: str) -> Tuple[str, int, float]:
    """Return the size of a website and the time to load it."""
    import requests
    from time import time
    start_time: float = time()
    page = requests.get(url).content
    duration: float = time() - start_time
    return url, len(page), duration


def sequential() -> Dict[str, Tuple[int, float]]:
    result = {}
    for url in sites:
        _, size, duration = fetch_site(url)
        result[url] = size, duration
    return result


def multiprocess() -> Dict[str, Tuple[int, float]]:
    from multiprocessing import Process, SimpleQueue
    queue = SimpleQueue()
    procs: List[Process] = []
    for url in sites:
        p = Process(target=lambda url, q: q.put(fetch_site(url)), args=(url, queue))
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
    result = {}
    while not queue.empty():
        url, size, duration = queue.get()
        result[url] = size, duration
    return result


def multiprocess2() -> Dict[str, Tuple[int, float]]:
    from multiprocessing import Pool
    result = {}
    pool = Pool()
    for url, size, duration in pool.imap_unordered(fetch_site, sites):
        result[url] = size, duration
    pool.close()
    return result


def multiprocess3() -> Dict[str, Tuple[int, float]]:
    from concurrent.futures import ProcessPoolExecutor
    result = {}
    with ProcessPoolExecutor() as pool:
        for url, size, duration in pool.map(fetch_site, sites):
            result[url] = size, duration
    return result


def multithread() -> Dict[str, Tuple[int, float]]:
    from concurrent.futures import ThreadPoolExecutor
    result = {}
    with ThreadPoolExecutor() as pool:
        for url, size, duration in pool.map(fetch_site, sites):
            result[url] = size, duration
    return result
