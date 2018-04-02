import logging
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from twisted.web import http

class RequestHandler(Resource):
    isLeaf = True
    def __init__(self, dispatcher):
        Resource.__init__(self)
        self.dispatcher = dispatcher

    def render(self, req):
        try:
            print "Accept a request " + req.path
            self.dispatcher.request(req)
        except:
            logging.error(req.method + " " + req.path + " " + str(http.INTERNAL_SERVER_ERROR))
            req.setResponseCode(http.INTERNAL_SERVER_ERROR)
            req.finish()
            raise
        return NOT_DONE_YET

class HTTPServer:
    def __init__(self, addresses, dispatcher):
        self.addresses = addresses
        self.dispatcher = dispatcher

    def start(self):
        from twisted.internet import reactor
        res = RequestHandler(self.dispatcher)
        factory = Site(res)
        for k,v in self.addresses.items():
            reactor.listenTCP(v, factory, 50, k)
        reactor.run()

