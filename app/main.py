from wsgiref import simple_server


def application(environ, start_response):
    status = "200 OK"
    body = "hello, world\n".encode('utf-8')
    headers = [
        ("Content-type", "text/plain; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    start_response(status, headers)
    return [body]


if __name__ == "__main__":
    host = ""
    port = 8000
    app = application
    server = simple_server.make_server(host, port, app)
    server.serve_forever()