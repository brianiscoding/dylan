from ctypes import *
from ctypes.util import find_library


lib = CDLL(find_library("nghttp2"))

NGHTTP2_NO_ERROR = 0
NGHTTP2_FLAG_NONE = 0
NGHTTP2_NV_FLAG_NONE = 0


class nghttp2_session(Structure):
    pass


class nghttp2_session_callbacks(Structure):
    pass


class nghttp2_nv(Structure):
    _fields_ = [
        ("name", POINTER(c_uint8)),
        ("value", POINTER(c_uint8)),
        ("namelen", c_size_t),
        ("valuelen", c_size_t),
        ("flags", c_uint8),
    ]


SEND_CB = CFUNCTYPE(
    c_ssize_t,
    POINTER(nghttp2_session),
    POINTER(c_uint8),
    c_size_t,
    c_int,
    c_void_p,
)

DATA_CB = CFUNCTYPE(
    c_int,
    POINTER(nghttp2_session),
    c_uint8,
    c_int32,
    POINTER(c_uint8),
    c_size_t,
    c_void_p,
)

CLOSE_CB = CFUNCTYPE(
    c_int,
    POINTER(nghttp2_session),
    c_int32,
    c_uint32,
    c_void_p,
)

lib.nghttp2_session_callbacks_new.argtypes = [
    POINTER(POINTER(nghttp2_session_callbacks))
]
lib.nghttp2_session_callbacks_del.argtypes = [POINTER(nghttp2_session_callbacks)]
lib.nghttp2_session_callbacks_set_send_callback2.argtypes = [
    POINTER(nghttp2_session_callbacks),
    SEND_CB,
]
lib.nghttp2_session_callbacks_set_on_data_chunk_recv_callback.argtypes = [
    POINTER(nghttp2_session_callbacks),
    DATA_CB,
]
lib.nghttp2_session_callbacks_set_on_stream_close_callback.argtypes = [
    POINTER(nghttp2_session_callbacks),
    CLOSE_CB,
]

lib.nghttp2_session_client_new.argtypes = [
    POINTER(POINTER(nghttp2_session)),
    POINTER(nghttp2_session_callbacks),
    c_void_p,
]

lib.nghttp2_submit_settings.argtypes = [
    POINTER(nghttp2_session),
    c_uint8,
    c_void_p,
    c_size_t,
]

lib.nghttp2_submit_request2.argtypes = [
    POINTER(nghttp2_session),
    c_void_p,
    POINTER(nghttp2_nv),
    c_size_t,
    c_void_p,
    c_void_p,
]

lib.nghttp2_session_send.argtypes = [POINTER(nghttp2_session)]
lib.nghttp2_session_mem_recv2.argtypes = [
    POINTER(nghttp2_session),
    POINTER(c_uint8),
    c_size_t,
]
lib.nghttp2_session_terminate_session.argtypes = [POINTER(nghttp2_session), c_uint32]
lib.nghttp2_session_del.argtypes = [POINTER(nghttp2_session)]

# Not used
lib.nghttp2_session_want_read.argtypes = [POINTER(nghttp2_session)]
lib.nghttp2_session_want_write.argtypes = [POINTER(nghttp2_session)]
