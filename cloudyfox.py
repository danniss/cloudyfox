from twisted.internet import epollreactor

epollreactor.install()

import config,domain_servlet, node_servlet, servlet, server, vnc_svr

from twisted.internet import reactor

if __name__ == "__main__":
    reactor.suggestThreadPoolSize(3)
    dispatcher = servlet.ServletDisptacher()
    dispatcher.registerServlet("/rest/domain", domain_servlet.DomainServlet())
    dispatcher.registerServlet("/rest/node", node_servlet.NodeServlet())
    server = server.HTTPServer({config.HTTP_SERVER_ADDRESS:config.HTTP_PORT}, dispatcher)
    reactor.listenTCP(config.VNC_SERVER_PORT, vnc_svr.VNCServerFactory(), 50, config.VNC_SERVER_ADDRESS)
    server.start()
