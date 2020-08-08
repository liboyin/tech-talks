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
