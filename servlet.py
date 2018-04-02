class Servlet:
    def __init__(self):
        pass

    def request(self, req):
        pass

class ServletFilter(Servlet):
    def __init__(self, parent):
        self.parent = parent

    def parent():
        return self.parent

from twisted.web import http
class ServletDisptacher(Servlet):
    def __init__(self):
        self.handlers = dict()

    def request(self, req):
        path = req.path
        while len(path) >= 0:
            handler = self.handlers.get(path)
            if handler != None:
                return handler.request(req)
            idx = path.rfind('/')
            if idx < 0:
                break
            path = path[0:idx]
        req.setResponseCode(http.NOT_FOUND)
        req.finish()

    def registerServlet(self, path, servlet):
        if len(path) > 0 and path[-1] == '/':
            path = path[0:-1]
        self.handlers[path] = servlet
