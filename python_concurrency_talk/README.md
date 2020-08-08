# Python Global Interpreter Lock and Concurrency

## Introduction

The Global Interpreter Lock (GIL) is a truly annoying part of Python. By definition, it is not a part of the Python language definition, but rather a part of the CPython interpreter. But thanks to the prevalence of CPython, developers almost always have to code with GIL in mind.

Other Python interpreters may or may not have GIL. Jython and IronPython, based on JVM and CLR respectively, do not have GIL. PyPy has GIL, but it also has an experimental branch that supports Software Transactional Memory (STM). Also note that other languages may have GIL too, especially those highly dynamic ones.

In this article, I'm going to explain how GIL affects Python multitasking, and various ways to improve the concurrency of the language.

## GIL in a Nutshell

GIL is defined in `ceval.c`. It was added in 1992 by Guido Van Rossum when he was experimenting with multi-threaded interpreter. He left an infamous comment:

```c
static PyThread_type_lock interpreter_lock = 0; /* This is the GIL */
```

Each interpreter process has exactly one GIL. When an interpreter starts, the main thread acquires the GIL. At any point in the lifetime of the interpreter process, the GIL is held by exactly one thread. When a thread holds the GIL, it executes Python bytecodes, while all other threads of the same interpreter sleep or wait for IO.

In short:

> At any point in time, each interpreter process can only execute one Python bytecode, no matter how many threads there are.

GIL simplifies interpreter implementation, optimises single-thread performance, and makes C extensions easier to integrate. Also, back in 1992, a single core CPU was a realistic assumption.

## Python Multitasking Model

Python uses system threads, so thread scheduling is managed by the operating system. Each interpreter process has a main thread and multiple user-defined child threads. With GIL, there are two types of multitasking:

### Cooperative multitasking

In cooperative multitasking, a thread voluntarily releases the GIL before IO, and re-acquires it afterwards. This is done in C code with `Py_BEGIN_ALLOW_THREADS` and `Py_END_ALLOW_THREADS` macro. When the thread is awaiting IO, another thread of the same interpreter can execute Python bytecodes. Cooperative multitasking improves the overall performance.

### Preemptive multitasking

In preemptive multitasking, the interpreter periodically interrupts the GIL-holding thread, allowing the operating system to re-schedule threads. In Python 2, this interval is every 100 bytecodes (`sys.getcheckinterval()`). In Python 3, this interval is 5 milliseconds (`sys.getswitchinterval()`). Preemptive multitasking allows concurrent execution of bytecodes, but does not improve performance.

## Concurrency is not Parallelism

Concurrency: multiple tasks start, run, and finish within an overlapping period.

```
Task A: running  -> running  -> await IO
Task B: await IO -> sleeping -> running
```

Parallelism: multiple tasks or several part of a unique task literally run at the same time.

```
Task A: running -> await IO -> running
Task B: running -> await IO -> running
```

## Removing the GIL

Clearly, the single-core CPU assumption of 1992 does not hold any longer. But removing the GIL has some major obstacles. Guido insisted that any attempt to remove the GIL must not slow down single-thread performance. Also, the community will not be happy if the removal of GIL mandates all C extensions to be rewritten. Regardless, there has been several attempts:

### Gilectomy

This project tries to replace the GIL with many local locks. The current performance of interpreter is significantly slower than CPython, mostly because of significantly higher cache failure rates.

### PyPy

An experimental branch of PyPy supports Software Transactional Memory (STM). If done properly, STM can solve most concurrency problems at once. However, it is extremely difficult to get right.

## Avoiding the GIL

Since removing the GIL from CPython is beyond the foreseeable future, the best practise is to work around it. There are two major solutions:

### Multiprocessing

Multiprocessing is to have multiple Python interpreters running in parallel, with each interpreter holding its own GIL. It is particularly useful in use cases that are: 1) CPU-intensive, and 2) subtasks requires little or no communication.

Multiprocessing and multithreading are the two ends of the same spectrum. Threads share memory space, so exchanging data is easy; but reading & writing data concurrently can also cause inconsistency, which is why we need locks. On the other hand, processes also have separate memory space, so they don't usually interfere with each other. The disadvantage of multiprocessing is that processes do not share memory, so inter-process communications usually have to go through serialisation, communication, and deserialisation.

Side note: Python has some support for sharing data among processes. See `multiprocessing.Value` and `multiprocessing.Array`.

### Avoid running Python bytecode

This can only be done out of Python, so it's a matter of choosing libraries. For example, `Cython ctypes` drops the GIL. Some NumPy functions drop the GIL. Numba can drop the GIL in JIT-ted code with the `nogil` parameter.

## Case Study: Batch Fetching Web Pages

### Sequential baseline

```python
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
```

The following solutions are ordered from low-level primitives to high-level wrapped APIs.

### Multiprocessing with explicit inter-process communication

```python
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
```

### Multiprocessing with a process pool

```python
def multiprocess2() -> Dict[str, Tuple[int, float]]:
    from multiprocessing import Pool
    result = {}
    pool = Pool()
    for url, size, duration in pool.imap_unordered(fetch_site, sites):
        result[url] = size, duration
    pool.close()
    return result
```

### Multiprocessing with ProcessPoolExecutor

```python
def multiprocess3() -> Dict[str, Tuple[int, float]]:
    from concurrent.futures import ProcessPoolExecutor
    result = {}
    with ProcessPoolExecutor() as pool:
        for url, size, duration in pool.map(fetch_site, sites):
            result[url] = size, duration
    return result
```

### Multithreading with ThreadPoolExecutor

In this use case, most time is spent on awaiting network IO. So a multi-threaded implementation is actually more suitable. This solution simply swapped out the `ProcessPoolExecutor` in the previous snippet for a `ThreadPoolExecutor`. This is a major advantage of the executor API.

```python
def multithread() -> Dict[str, Tuple[int, float]]:
    from concurrent.futures import ThreadPoolExecutor
    result = {}
    with ThreadPoolExecutor() as pool:
        for url, size, duration in pool.map(fetch_site, sites):
            result[url] = size, duration
    return result
```

## Locks in Multithreading

As a principle, Python commands (not bytecodes) are not atomic, but context switch can happen between any bytecodes. Therefore, in a multithreaded environment, all critical sections must be guarded by locks. This code snippet demonstrates explicit locking and unlocking in a concurrent counter.

```python
import threading

counter_lock = threading.Lock()
printer_lock = threading.Lock()
counter = 0

def worker():
    global counter
    with counter_lock:
        counter += 1
        with printer_lock:
            print(f'counter = {counter}')

with printer_lock:
    print('starting threads')
threads = []
for i in range(10):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)
for t in threads:
    t.join()
with printer_lock:
    print('done!')
```

## Asynchronous Programming

Asynchronous programming is based on coroutines, also named lightweight threads or green threads. Coroutines are thread-like things that run concurrently, but not in parallel. The primary difference between coroutines and threads is that coroutines always context-switch cooperatively. In Python, coroutines are implemented with generators. This means Python coroutines are normal Python functions running in a single thread; and scheduling is done by the Python interpreter. This means the scheduling cost of coroutines is much lower than that of system threads, and scheduling can be done in a context-aware manner.

But asynchronous programming in Python also has some significant drawbacks. Most importantly, developing with async requires the whole ecosystem to be async. It's common to find two functionally identical packages with the only difference being one is synchronous, while the other one is asynchronous. This also means that integrating async with other concurrency models can be very difficult.

Asynchronous features are only available after Python 3.4.

### Boilerplate code

```python
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
```

### Explicit construction of Futures

```python
def coroutine() -> Dict[str, Tuple[int, float]]:
    loop = asyncio.get_event_loop()
    tasks = []
    for url in sites:
        t = asyncio.ensure_future(fetch_site(url))
        tasks.append(t)
    done, _ = loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
    return get_result(done)
```

### Automatic construction of Futures

```python
def coroutine2() -> Dict[str, Tuple[int, float]]:
    loop = asyncio.get_event_loop()
    done, _ = loop.run_until_complete(asyncio.wait(map(fetch_site, sites)))
    loop.close()
    return get_result(done)
```

### Automatic construction of event loop and Futures (Python 3.7)

```python
def coroutine3() -> Dict[str, Tuple[int, float]]:
    done, _ = asyncio.run(asyncio.wait(map(fetch_site, sites)))
    return get_result(done)
```

## References

* [https://docs.python.org/3/library/multiprocessing.html](https://docs.python.org/3/library/multiprocessing.html)
* [https://docs.python.org/3/library/concurrent.futures.html](https://docs.python.org/3/library/concurrent.futures.html)
* [https://docs.python.org/3/library/threading.html](https://docs.python.org/3/library/threading.html)
* [https://docs.python.org/3/library/queue.html](https://docs.python.org/3/library/queue.html)
* [https://docs.python.org/3/library/asyncio-task.html](https://docs.python.org/3/library/asyncio-task.html)
* http://www.drdobbs.com/open-source/concurrency-and-python/206103078
* Dave Beazley: Understanding the Python GIL, PyCon 2010
    * [https://www.youtube.com/watch?v=Obt-vMVdM8s](https://www.youtube.com/watch?v=Obt-vMVdM8s)
    * [https://www.dabeaz.com/python/UnderstandingGIL.pdf](https://www.dabeaz.com/python/UnderstandingGIL.pdf)
* Dave Beazley: Embracing the Global Interpreter Lock (GIL), PyCodeConf 2011
    * [https://www.youtube.com/watch?v=fwzPF2JLoeU](https://www.youtube.com/watch?v=fwzPF2JLoeU)
* Larry Hastings: Python's Infamous GIL, PyCon 2015
    * [https://www.youtube.com/watch?v=KVKufdTphKs](https://www.youtube.com/watch?v=KVKufdTphKs)
* Larry Hastings: Removing Python's GIL: The Gilectomy, PyCon 2016
    * [https://www.youtube.com/watch?v=P3AyI_u66Bw](https://www.youtube.com/watch?v=P3AyI_u66Bw)
* A Jesse Jiryu Davis: Grok the GIL Write Fast And Thread Safe Python, PyCon 2017
    * [https://www.youtube.com/watch?v=7SSYhuk5hmc](https://www.youtube.com/watch?v=7SSYhuk5hmc)
* Raymond Hettinger: Keynote on Concurrency, PyBay 2017
    * [https://www.youtube.com/watch?v=9zinZmE3Ogk](https://www.youtube.com/watch?v=9zinZmE3Ogk)
    * [https://pybay.com/site_media/slides/raymond2017-keynote/index.html](https://pybay.com/site_media/slides/raymond2017-keynote/index.html)
* Dave Beazley: Fear and Awaiting in Async: A Savage Journey to the Heart of the Coroutine Dream
    * [https://www.youtube.com/watch?v=E-1Y4kSsAFc](https://www.youtube.com/watch?v=E-1Y4kSsAFc)
* Robert Smallshire: Coroutine Concurrency in Python 3 with asyncio
    * [https://www.youtube.com/watch?v=c5wodlqGK-M](https://www.youtube.com/watch?v=c5wodlqGK-M)