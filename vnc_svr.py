import libvirt, libxml2

from twisted.internet import protocol, reactor

import util

class VNCClientProtocol(protocol.Protocol):
    def __init__(self, remote):
        self.remote = remote

    def connectionMade(self):
        self.remote.vncClient(self)

    def dataReceived(self, data):
        self.remote.transport.write(data)

class VNCClientFactory(protocol.ClientFactory):

    def __init__(self, p):
        self.remote = p

    def remote(self):
        return self.remote

    def startedConnecting(self, connector):
        pass

    def buildProtocol(self, addr):
        return VNCClientProtocol(self.remote)

    def clientConnectionLost(self, connector, reason):
        self.remote.transport.loseConnection()

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        self.remote.transport.loseConnection()

class VNCServerProtocol(protocol.Protocol):
    def connectionMade(self):
         self.data = ''
         self.client = None

    def dataReceived(self, data):
        if self.client == None:
            self.data += data
            idx = self.data.find('\n')
            if idx > 0:
                uuid = self.data[0:idx]
                port = self.getPort(uuid)
                if port == None:
                    self.transport.loseConnection()
                self.data = self.data[idx + 1:]
                reactor.connectTCP('localhost', port, VNCClientFactory(self))
        else:
            self.client.transport.write(data)

    def getPort(self, uuid):
        conn = util.getConnection()
        try:
            domain = conn.lookupByUUIDString(uuid)
            doc = libxml2.parseDoc(domain.XMLDesc(0))
            graphics = doc.xpathEval('//graphics')
            if len(graphics) == 0:
                return None
            for graphic in graphics:
                if graphic.prop('type') == 'vnc':
                    return int(graphic.prop('port'))
        finally:
            conn.close()    
        return None

    def vncClient(self, c):
        self.client = c
        if len(self.data) > 0:
            self.client.transport.write(self.data)

class VNCServerFactory(protocol.ServerFactory):
    protocol = VNCServerProtocol

