import mimetypes
import socket
import logging
from urllib.parse import urlparse, unquote_plus
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from multiprocessing import Process
from datetime import datetime
from pymongo.mongo_client import MongoClient


URI = "mongodb://mongodb:27017"
BASE_DIR = Path(__file__).parent
BUFFER_SIZE = 1024
HTTP_HOST = '0.0.0.0'
HTTP_PORT = 3000
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000


class MyFramework(BaseHTTPRequestHandler):
    def do_GET(self):
        router = urlparse(self.path).path
        match router:
            case "/":
                self.send_html("index.html")
            case "/message":
                self.send_html("message.html")
            case _:
                file = BASE_DIR.joinpath(router[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html("error.html", 404)

    def do_POST(self):
        size = self.headers.get("Content-Length")
        data = self.rfile.read(int(size)).decode()

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data.encode(), (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def send_html(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())

    def send_static(self, filename, status=200):
        self.send_response(status)
        mimetype = mimetypes.guess_type(filename)[0] if mimetypes.guess_type(filename)[0] else "text/plain"
        self.send_header("Content-type", mimetype)
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())


def save_data(data):
    client = MongoClient(URI)
    db = client.final_home_work
    parse_data = unquote_plus(data.decode())
    current_time = datetime.now()
    collected_data = {"date": current_time}
    try:
        pass
        parse_data = {key: value for key, value in
                      [el.split("=") for el in parse_data.split("&")]}
        collected_data.update(parse_data)
        print(collected_data)
        db.messages.insert_one(collected_data)
    except ValueError as e:
        logging.error(f"Parse error: {e}")
    except Exception as e:
        logging.error(f"Failed to save: {e}")
    finally:
        client.close()


def run_http_server():
    httpd = HTTPServer((HTTP_HOST, HTTP_PORT), MyFramework)
    try:
        logging.info(f"Server started on http://{HTTP_HOST}:{HTTP_PORT}")
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"Server error: {e}")
    finally:
        logging.info("Server stopped")
        httpd.server_close()


def run_socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SOCKET_HOST, SOCKET_PORT))
    logging.info(f"Server started on socket://{SOCKET_HOST}:{SOCKET_PORT}")
    try:
        while True:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            logging.info(f"Get message from {addr}: {data.decode()}")
            save_data(data)
    except Exception as e:
        logging.error(f"Server error: {e}")
    finally:
        logging.info("Server stopped")
        sock.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(processName)s - %(message)s")
    http_process = Process(target=run_http_server, args=())
    http_process.start()

    socket_process = Process(target=run_socket_server, args=())
    socket_process.start()

    http_process.join()
    socket_process.join()
