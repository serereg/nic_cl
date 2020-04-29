from multiprocessing import Process

from torpy.cli.socks import SocksServer
from torpy.client import TorClient


class TorSocketProcess(Process):
    def __init__(self, ip, port, hops):
        super().__init__()
        self.ip = ip
        self.port = port
        self.hops = hops

    def run(self):
        client = TorClient()
        with client.create_circuit(self.hops) as circuit:
            with SocksServer(circuit, self.ip, self.port) as socks_serv:
                socks_serv.start()
