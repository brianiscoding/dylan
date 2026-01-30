import socket
import ssl
from ctypes import *
from bindings import *
import sys
from typing import Any
from configure import get_config
import constants as c


class HTTP2Client:
    def __init__(self, scheme, host, path, port, verbose=False):
        self.scheme = scheme
        self.host = host
        self.path = path
        self.port = port
        self.verbose = verbose

        self.streams = {}
        self.sock = self._create_socket()
        # must store callbacks, otherwise get segfaulted
        self.callbacks = self._create_callbacks()
        self.session = self._create_session()
        self._send_settings_and_headers()
        self._get()
        self._cleanup()

    def _create_socket(self) -> Any:
        # Create and establish a socket connection to the host
        try:
            raw = socket.create_connection((self.host, self.port))
            # http standard
            if self.port == c.DEFAULT_HTTP_PORT:
                return raw
            # https standard
            elif self.port == c.DEFAULT_HTTPS_PORT:
                ctx = ssl.create_default_context()
                ctx.set_alpn_protocols([c.ALPN_H2])
                sock = ctx.wrap_socket(raw, server_hostname=self.host)
                assert sock.selected_alpn_protocol() == c.ALPN_H2
                return sock
            else:
                raise
        except:
            print("ERROR: create_socket")
            sys.exit(1)

    def _create_callbacks(self):
        # these cbs contain args that are not used, but must not be deleted bc they are defined as such in the nghttp2 library
        def send_cb(
            session: Any, data: Any, length: int, flags: int, user_data: Any
        ) -> int:
            # Callback function for sending data through the socket
            sock = cast(user_data, POINTER(py_object)).contents.value
            sock.sendall(string_at(data, length))
            return length

        def data_cb(
            session: Any,
            flags: int,
            stream_id: int,
            data: Any,
            length: int,
            user_data: Any,
        ) -> int:
            # Callback function for receiving data from HTTP/2 stream
            if stream_id not in self.streams:
                self.streams[stream_id] = False
            if self.verbose:
                print(string_at(data, length).decode(errors="ignore"), end="")
            return 0

        def close_cb(
            session: Any, stream_id: int, error_code: int, user_data: Any
        ) -> int:
            # Callback function invoked when a stream is closed
            self.streams[stream_id] = True
            return 0

        # Saved or else segfaulted
        return {
            "send": SEND_CB(send_cb),
            "data": DATA_CB(data_cb),
            "close": CLOSE_CB(close_cb),
        }

    def _create_session(self) -> Any:
        # Create an nghttp2 session with configured callbacks
        callbacks = POINTER(nghttp2_session_callbacks)()
        lib.nghttp2_session_callbacks_new(byref(callbacks))
        lib.nghttp2_session_callbacks_set_send_callback2(
            callbacks, self.callbacks["send"]
        )
        lib.nghttp2_session_callbacks_set_on_data_chunk_recv_callback(
            callbacks, self.callbacks["data"]
        )
        lib.nghttp2_session_callbacks_set_on_stream_close_callback(
            callbacks, self.callbacks["close"]
        )

        session = POINTER(nghttp2_session)()
        user_data = py_object(self.sock)

        lib.nghttp2_session_client_new(
            byref(session), callbacks, cast(pointer(user_data), c_void_p)
        )

        lib.nghttp2_session_callbacks_del(callbacks)
        return session

    def _nv(self, name: str, value: str) -> Any:
        # Create an nghttp2 name-value pair for headers
        nb = name.encode()
        vb = value.encode()
        return nghttp2_nv(
            cast(c_char_p(nb), POINTER(c_uint8)),
            cast(c_char_p(vb), POINTER(c_uint8)),
            len(nb),
            len(vb),
            NGHTTP2_NV_FLAG_NONE,
        )

    def _send_settings_and_headers(self) -> None:
        # Send HTTP/2 settings frame and request headers
        headers = (nghttp2_nv * c.NUM_HEADERS)(
            self._nv(":method", "GET"),
            self._nv(":scheme", self.scheme),
            self._nv(":authority", self.host),
            self._nv(":path", self.path),
        )

        # blank settings for minimal
        lib.nghttp2_submit_settings(
            self.session, NGHTTP2_FLAG_NONE, c.NULL_SETTINGS_PTR, c.ZERO_SETTINGS
        )
        # queue up to send
        lib.nghttp2_submit_request2(
            self.session,
            c.NULL_PRIORITY,
            headers,
            c.NUM_HEADERS,
            c.NULL_USER_DATA_PTR,
            c.NULL_DATA_PROVIDER,
        )
        # then send to the frames
        lib.nghttp2_session_send(self.session)

    def _get(self) -> None:
        # Receive and process HTTP/2 response data from the server
        while True:
            if self.streams and all(self.streams[k] for k in self.streams):
                break
            data = self.sock.recv(c.RECV_BUFFER_SIZE)
            if not data:
                continue

            buf = (c_uint8 * len(data)).from_buffer_copy(data)
            lib.nghttp2_session_mem_recv2(self.session, buf, len(data))
            lib.nghttp2_session_send(self.session)

    def _cleanup(self) -> None:
        # Close the HTTP/2 session and socket connection
        lib.nghttp2_session_terminate_session(self.session, NGHTTP2_NO_ERROR)
        lib.nghttp2_session_send(self.session)
        lib.nghttp2_session_del(self.session)
        self.sock.close()


def main() -> None:
    cfg = get_config()
    HTTP2Client(
        scheme=cfg["scheme"],
        host=cfg["host"],
        path=cfg["path"],
        port=cfg["port"],
        verbose=cfg["verbose"],
    )


if __name__ == "__main__":
    main()
