import socket
import ssl
from ctypes import *
from bindings import *
import sys
from typing import Any, Dict


def _send_cb(session: Any, data: Any, length: int, flags: int, user_data: Any) -> int:
    # Callback function for sending data through the socket
    sock = cast(user_data, POINTER(py_object)).contents.value
    sock.sendall(string_at(data, length))
    return length


def _data_cb(
    session: Any, flags: int, stream_id: int, data: Any, length: int, user_data: Any
) -> int:
    # Callback function for receiving data from HTTP/2 stream
    global streams, silent
    if stream_id not in streams:
        streams[stream_id] = False
    if not silent:
        print(string_at(data, length).decode(errors="ignore"), end="")
    return 0


def _close_cb(session: Any, stream_id: int, error_code: int, user_data: Any) -> int:
    # Callback function invoked when a stream is closed
    global streams
    streams[stream_id] = True
    return 0


# Saved or else segfaulted
send_cb_c = SEND_CB(_send_cb)
data_cb_c = DATA_CB(_data_cb)
close_cb_c = CLOSE_CB(_close_cb)
# Track to know when to close
streams: Dict[int, bool] = {}
silent: bool = False


def _create_socket(host: str, port: int) -> Any:
    # Create and establish a socket connection to the host
    try:
        raw = socket.create_connection((host, port))
        if port == 80:
            return raw

        elif port == 443:
            ctx = ssl.create_default_context()
            ctx.set_alpn_protocols(["h2"])
            sock = ctx.wrap_socket(raw, server_hostname=host)
            assert sock.selected_alpn_protocol() == "h2"
            return sock

        else:
            raise
    except:
        print("ERROR: create_socket")
        sys.exit(1)


def _create_session(sock: Any) -> Any:
    # Create an nghttp2 session with configured callbacks
    callbacks = POINTER(nghttp2_session_callbacks)()
    lib.nghttp2_session_callbacks_new(byref(callbacks))
    lib.nghttp2_session_callbacks_set_send_callback2(callbacks, send_cb_c)
    lib.nghttp2_session_callbacks_set_on_data_chunk_recv_callback(callbacks, data_cb_c)
    lib.nghttp2_session_callbacks_set_on_stream_close_callback(callbacks, close_cb_c)

    session = POINTER(nghttp2_session)()
    user_data = py_object(sock)

    lib.nghttp2_session_client_new(
        byref(session), callbacks, cast(pointer(user_data), c_void_p)
    )

    lib.nghttp2_session_callbacks_del(callbacks)
    return session


def _nv(name: str, value: str) -> Any:
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


def _send_settings_and_headers(session: Any, scheme: str, host: str) -> None:
    # Send HTTP/2 settings frame and request headers
    headers = (nghttp2_nv * 4)(
        _nv(":method", "GET"),
        _nv(":scheme", scheme),
        _nv(":authority", host),
        _nv(":path", "/"),
    )

    lib.nghttp2_submit_settings(session, NGHTTP2_FLAG_NONE, None, 0)
    lib.nghttp2_submit_request2(session, None, headers, 4, None, None)
    lib.nghttp2_session_send(session)


def _get(sock: Any, session: Any) -> None:
    # Receive and process HTTP/2 response data from the server
    global streams
    while True:
        if streams and all(streams[k] for k in streams):
            break
        data = sock.recv(1000)
        if not data:
            continue

        buf = (c_uint8 * len(data)).from_buffer_copy(data)
        lib.nghttp2_session_mem_recv2(session, buf, len(data))
        lib.nghttp2_session_send(session)


def _cleanup(sock: Any, session: Any) -> None:
    # Close the HTTP/2 session and socket connection
    lib.nghttp2_session_terminate_session(session, NGHTTP2_NO_ERROR)
    lib.nghttp2_session_send(session)
    lib.nghttp2_session_del(session)
    sock.close()


def client(host: str, port: int, scheme: str, silent_: bool = False) -> None:
    # Main HTTP/2 client function that coordinates the entire request-response cycle
    global silent
    silent = silent_

    sock = _create_socket(host, port)
    session = _create_session(sock)
    _send_settings_and_headers(session, scheme, host)
    _get(sock, session)
    _cleanup(sock, session)
