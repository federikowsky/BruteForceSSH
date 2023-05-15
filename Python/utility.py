import ipaddress


class Utility:
    def __init__(self, host: str, port: int, file: str):
        self.host: str = host
        self.port: int = port
        self.file: str = file
        self.find_error()
        
    def show_error(self, type, message):
        print(f"Error: {type}: {message}")
        exit(1)
        
    def find_error(self):
        methods = [method for method in dir(Utility) if "check" in method]
        for method in methods:
            # get callable method and run it
            getattr(self, method)()
        
    def check_host(self):
            if self.host == 'localhost':
                return
            try:
                ipaddress.IPv4Address(self.host)
            except ipaddress.AddressValueError as e:
                self.show_error("HOST", e)

    def check_ssh_port(self):
        if self.port <= 0 or self.port >= 65535:
            self.show_error("PORT", "ssh port must be between 0 and 65535")

    def check_wordlist(self):
        try:
            open(self.file, "r", encoding='utf-8')
        except Exception as e:
            self.show_error("FILE", e)
