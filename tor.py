from multiprocessing import Process

from torpy.cli.socks import SocksServer
from torpy.client import TorClient


class TorSocketProcess(Process):
    def __init__(self, ip="127.0.0.1", port=9050, hops=3):
        super().__init__()
        self.ip = ip
        self.port = port
        self.hops = hops
        self.client = TorClient()

    def run(self):
        with self.client.create_circuit(self.hops) as circuit:
            with SocksServer(circuit, self.ip, self.port) as socks_serv:
                socks_serv.start()
