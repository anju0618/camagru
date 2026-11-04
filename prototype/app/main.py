import logging
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from . import db, handlers  # noqa: F401  (importing handlers registers the routes)
from .web import application


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


class ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main():
    logging.basicConfig(level=logging.ERROR)
    db.init()
    with make_server("", 8000, application, server_class=ThreadedServer,
                     handler_class=QuietHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
