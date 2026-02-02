import socket
import ssl
from ctypes import *
from bindings import *
from typing import Any, Dict, Optional, Union
import constants as c
import time
from urllib.parse import urlparse
import sys


class HTTP2Client:
    def __init__(
        self,
        url: str,
    ) -> None:
        self.url: str = url
        self.scheme: Optional[c.SCHEMES] = None
        self.host: Optional[str] = None
        self.path: Optional[str] = None
        self.port: Optional[c.PORTS] = None

        self.data: Optional[str] = None
        self.time: Optional[float] = None

        self._sock: Optional[Union[socket.socket, ssl.SSLSocket]] = None
        self._session: Optional[Any] = None
        self._is_alive_by_stream_id: Dict[int, bool] = {}
        # must store callbacks, otherwise get segfaulted
        self._callbacks: Optional[list[callable]] = None
        self._raw_data: bytearray = bytearray()

        try:
            self._parse_url()
            self._create_socket()
            self._create_session()
            self._send_headers()
            self._get()
        finally:
            self._cleanup()

    def _parse_url(self) -> None:
        """
        Parse the URL and set scheme, host, path, and port attributes.
        """
        parsed = urlparse(self.url)
        self.scheme = parsed.scheme
        self.host = parsed.netloc
        self.path = parsed.path if parsed.path != "" else "/"
        self.port = c.PORT_BY_SCHEME[parsed.scheme]
        if not parsed.scheme or not parsed.netloc:
            raise Exception(f"Invalid URL: {self.url}.")

    def _create_socket(self) -> None:
        """
        Create a socket connection to the specified host and port.
        """
        try:
            raw = socket.create_connection((self.host, self.port))
            if self.port == c.DEFAULT_HTTP_PORT:
                # plain socket
                self._sock = raw
                return

            if self.port == c.DEFAULT_HTTPS_PORT:
                # ssl socket
                ctx = ssl.create_default_context()
                ctx.set_alpn_protocols([c.ALPN_H2])
                sock = ctx.wrap_socket(raw, server_hostname=self.host)

                if sock.selected_alpn_protocol() != c.ALPN_H2:
                    raise Exception("ALPN negotiation failed.")
                self._sock = sock
                return

            raise Exception("Unsupported port.")
        except socket.timeout:
            raise ConnectionError(f"Timeout.")
        except socket.gaierror:
            raise ConnectionError(f"Could not resolve host.")

    def _create_session(self) -> None:
        """
        Create an nghttp2 session with necessary callbacks.
        """

        def send_cb(
            session: Any,
            data: Any,  # bindings.LP_c_ubyte
            length: int,
            flags: int,
            user_data: Any,
        ) -> int:
            """
            Callback function for sending data through the socket.
            """
            sock = cast(user_data, POINTER(py_object)).contents.value
            sock.sendall(string_at(data, length))
            return length

        def data_cb(
            session: Any,
            flags: int,
            stream_id: int,
            data: Any,  # bindings.LP_c_ubyte
            length: int,
            user_data: Any,
        ) -> int:
            """
            Callback function for receiving data from HTTP/2 stream.
            """
            if stream_id not in self._is_alive_by_stream_id:
                self._is_alive_by_stream_id[stream_id] = False
            self._raw_data.extend(string_at(data, length))
            return 0

        def close_cb(
            session: Any, stream_id: int, error_code: int, user_data: Any
        ) -> int:
            """
            Callback function invoked when a stream is closed
            """
            self._is_alive_by_stream_id[stream_id] = True
            return 0

        send_cb_ = SEND_CB(send_cb)
        data_cb_ = DATA_CB(data_cb)
        close_cb_ = CLOSE_CB(close_cb)
        self._callbacks = [send_cb_, data_cb_, close_cb_]

        cbs = POINTER(nghttp2_session_callbacks)()
        lib.nghttp2_session_callbacks_new(byref(cbs))
        lib.nghttp2_session_callbacks_set_send_callback2(cbs, send_cb_)
        lib.nghttp2_session_callbacks_set_on_data_chunk_recv_callback(cbs, data_cb_)
        lib.nghttp2_session_callbacks_set_on_stream_close_callback(cbs, close_cb_)

        session = POINTER(nghttp2_session)()
        user_data = py_object(self._sock)

        lib.nghttp2_session_client_new(
            byref(session), cbs, cast(pointer(user_data), c_void_p)
        )

        self._session = session

    def _create_name_value(self, name: str, value: str) -> Any:
        """
        Create an nghttp2 name-value pair for HTTP/2 headers.
        """
        name_binary = name.encode()
        value_binary = value.encode()
        return nghttp2_nv(
            cast(c_char_p(name_binary), POINTER(c_uint8)),
            cast(c_char_p(value_binary), POINTER(c_uint8)),
            len(name_binary),
            len(value_binary),
            c.NGHTTP2_NV_FLAG_NONE,
        )

    def _send_headers(self) -> None:
        """
        Send HTTP/2 settings frame and request headers.
        """
        # can be extended
        headers_array = [
            (":method", "GET"),
            (":scheme", self.scheme),
            (":authority", self.host),
            (":path", self.path),
        ]
        num_headers = len(headers_array)
        headers = (nghttp2_nv * num_headers)(
            *[self._create_name_value(name, value) for name, value in headers_array]
        )

        # blank settings for mvp
        lib.nghttp2_submit_settings(
            self._session, c.NGHTTP2_FLAG_NONE, c.NULL_SETTINGS_PTR, c.ZERO_SETTINGS
        )
        lib.nghttp2_submit_request2(
            self._session,
            c.NULL_PRIORITY,
            headers,
            num_headers,
            c.NULL_USER_DATA_PTR,
            c.NULL_DATA_PROVIDER,
        )
        lib.nghttp2_session_send(self._session)

    def _get(self) -> None:
        """
        Perform the HTTP/2 GET request and process incoming data.
        """
        start_time: float = time.monotonic()
        deadline: float = start_time + c.TIMEOUT

        while time.monotonic() < deadline:
            if self._is_alive_by_stream_id and all(
                self._is_alive_by_stream_id.values()
            ):
                self.data = self._raw_data.decode(errors="ignore")
                self.time = time.monotonic() - start_time
                return
            # bytes
            data = self._sock.recv(c.RECV_BUFFER_SIZE)
            if not data:
                time.sleep(c.NO_DATA_SLEEP)
                continue

            buf = (c_uint8 * len(data)).from_buffer_copy(data)
            lib.nghttp2_session_mem_recv2(self._session, buf, len(data))
            lib.nghttp2_session_send(self._session)

        raise Exception("Timeout exceeded.")

    def _cleanup(self) -> None:
        """
        Close the HTTP/2 session and socket connection.
        """
        if self._session is not None:
            lib.nghttp2_session_terminate_session(self._session, c.NGHTTP2_NO_ERROR)
            lib.nghttp2_session_send(self._session)
            lib.nghttp2_session_del(self._session)
            self._session = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self._callbacks is not None:
            self._callbacks = None
        if self._raw_data is not None:
            self._raw_data = bytearray()


def main() -> None:
    url = sys.argv[1]
    client = HTTP2Client(url=url)
    if "--verbose" in sys.argv:
        print(client.data)


if __name__ == "__main__":
    main()
