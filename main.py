#!/usr/bin/env python3
import sys
import socket
from typing import List, Optional

url = sys.argv[1]  # get sys args


class _curlClone:
    class __url:
        def __init__(self, url: str) -> None:  # constructor
            self._url, self._port = (url, None)
            self._subdomains = ["http", "https"]
            self._netloc, self._path = (None, None)
            pass

        #
        # _isHTTP()
        def _isHTTP(self, parsed: str) -> bool:
            if parsed != self._subdomains[0]:
                print("Error: HTTPS scheme entered. Exiting.")
                return False
            return True

        #
        # _isValidURL()
        def _isValidURL(self, parsed: List[str]) -> bool:
            if parsed[0] not in self._subdomains:
                return False
            return self._isHTTP(parsed[0])

        #
        # _hostParse()
        def _hostParse(self) -> None:
            if ":" not in self._netloc:
                self._port = 80  # no port to parse
                return None
            split = self._netloc.split(":")
            self._netloc, self._port = split[0], int(split[1])
            pass

        #
        # _urlParse()
        def _urlParse(self) -> None:
            http_parsed = self._url.split("://")
            # print(http_parsed)
            # Base Case 1: Non-HTTP / Non-HTTPS
            if not self._isValidURL(http_parsed):
                sys.exit("[Error -1]: Invalid Scheme Provided")

            # Step 2: Separate hostname and path
            http_parsed = "".join(http_parsed[1:])
            http_parsed = http_parsed.split("/")
            # print(http_parsed)
            self._netloc = http_parsed[0]

            # Step 3: Join path together again
            path = "/".join(http_parsed[1:])
            # print(path)
            self._path = path
            pass

        #
        # getPath()
        def getPath(self) -> str:
            return self._path

        #
        # getHost()
        def getHost(self) -> str:
            return self._netloc

        #
        # getPort()
        def getPort(self) -> int:
            return self._port

        #
        # setURL()
        def setURL(self, url: str) -> None:
            self._url = url
            self._urlParse()
            self._hostParse()

        #
        # getURL()
        def getURL(self) -> str:
            return self._url

    def __init__(self, url, port=443) -> None:  # constructor
        self._s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self._port, self._url = port, self.__url(url)
        self._hostname, self._ipaddr = None, None
        self._path, self._data = None, None
        self._content_length = None
        self._redirects = [
            "HTTP/1.0 301 Moved Permanently",
            "HTTP/1.0 302 Found",
            "HTTP/1.1 301 Moved Permanently",
            "HTTP/1.1 302 Found",
        ]
        self._url.setURL(url)
        self._port = self._url.getPort()
        self._path = self._url.getPath()
        self._original_length = 0

        try:
            host_tuple = socket.gethostbyname_ex(self._url.getHost())
            # print(host_tuple)
            if host_tuple[1]:
                self._hostname = host_tuple[1][0]  # gets official hostname (not alias)
            else:
                self._hostname = host_tuple[0]
            self._ipaddr = host_tuple[-1][0]

            # self.hostname returns a tuple (hostname, aliaslist[str],
            # ipaddrlist[str])
            # print(self._hostname, self._ipaddr, self._port, self._path)
        except socket.gaierror:
            sys.exit(f"[Error 2] Name or service '{self._url.getHost()}' not known")
        pass

    #
    # _parseData()
    def _parseData(self, header=False) -> None:
        self._data = self._data.decode().splitlines()
        html = self._data.index("")
        for line in self._data[html + 1 :]:
            print(line)

    #
    # _checkData()
    def _checkData(self) -> None:
        # Check 1: Proper Response:
        status_code = int(self._data[0].split(" ")[1])
        if status_code >= 400:
            sys.exit("[Error 5]: Received 4xx status code. Exiting.")

        # Check 2: Content-Type
        for i in range(len(self._data)):
            if "Content-Type:" in self._data[i]:
                content_type = self._data[i].split(";")[0].split(" ")[-1]
                if content_type == "text/html":
                    return

                else:
                    sys.exit("[Error 3]: Non-text/html response. Exiting.")
        return

    #
    # _checkRedirect()
    def _checkRedirect(self):
        for line in self._data:
            if line in self._redirects:
                return True
        return False

    #
    # _redirect()
    def _redirect(self) -> None:
        for i in range(len(self._data)):
            if "Location:" in self._data[i]:
                new_url = self._data[i].split(" ")[1]
        self._url.setURL(new_url)
        self._port = self._url.getPort()
        self._path = self._url.getPath()

        host_tuple = socket.gethostbyname_ex(self._hostname)
        print(f"new tuple: {host_tuple}")
        self._hostname = host_tuple[0]
        self._ipaddr = host_tuple[-1][0]
        # print(self._hostname, self._ipaddr, self._port, self._path)
        pass

    #
    # _send()
    def _send(self) -> None:
        self._s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self._s.connect((self._ipaddr, self._port))

        request = f"GET /{self._path} HTTP/1.0\r\nHost: {self._hostname}\r\n\r\n"
        print(request)
        self._s.send(request.encode())

    #
    # _checkHTML()
    def _checkHTML(self) -> bool:
        data_copy = self._data.decode().splitlines()
        if "</html>" in data_copy[-1]:
            return True
        return False

    #
    # _receive()
    def _receive(self) -> None:
        self._original_length = self._content_length
        buffer_size = 512
        if self._content_length:
            while True:
                stream = self._s.recv(buffer_size)
                if self._content_length < 0:
                    if self._checkHTML():
                        self._data += stream
                        self._s.close()
                        break
                    else:
                        self._content_length = self._original_length // 4
                        self._receive()
                    break
                self._data += stream
                self._content_length = self._content_length - buffer_size
        else:
            while True:
                stream = self._s.recv(buffer_size)
                if not len(stream):
                    self._data += stream
                    self._s.close()
                    break
                self._data += stream

    #
    # retrieveHeader
    def _retrieveHeader(self):
        self._data = b""
        buffer_size = 1024
        stream = self._s.recv(buffer_size)
        self._data += stream
        stream = stream.decode().splitlines()
        for line in stream:
            if "Content-Length" in line:
                self._content_length = int(line.split(" ")[-1])
            else:
                continue

    #
    # curl()
    def curl(self):
        try:
            prevStatus = None

            # print(f"this is path:{self._path}, this is hostname: {self._hostname}")
            self._send()
            self._retrieveHeader()
            self._receive()
            self._parseData()
            self._checkData()

            counter = 1
            # Handle redirects
            while self._checkRedirect() and counter < 10:
                counter += 1
                self._redirect()
                print(f"Redirected to: {self._url.getURL()}")

                self._send()
                self._retrieveHeader()
                self._receive()
                self._parseData()
                self._checkData()

            if self._checkRedirect():
                sys.exit("[Error 4]: Over 10 redirects attempted. Exiting.")

            # print(self._content_length)
            # print(self._original_length)
            sys.exit(0)  # SUCCESS

        except KeyboardInterrupt:
            sys.exit("Program exited by user")


if __name__ == "__main__":
    clone = _curlClone(url)
    clone.curl()
