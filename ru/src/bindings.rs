use libc::size_t;
use std::os::raw::{c_int, c_void};

#[repr(C)]
pub struct nghttp2_session {
    _private: [u8; 0],
}

#[repr(C)]
pub struct nghttp2_session_callbacks {
    _private: [u8; 0],
}

//
// Structs
//
#[repr(C)]
pub struct nghttp2_nv {
    pub name: *const u8,
    pub value: *const u8,
    pub namelen: size_t,
    pub valuelen: size_t,
    pub flags: u8,
}

//
// Callback types
//
pub type SendCallback = Option<
    unsafe extern "C" fn(
        session: *mut nghttp2_session,
        data: *const u8,
        length: size_t,
        flags: c_int,
        user_data: *mut c_void,
    ) -> size_t,
>;

pub type DataCallback = Option<
    unsafe extern "C" fn(
        session: *mut nghttp2_session,
        flags: u8,
        stream_id: i32,
        data: *const u8,
        length: size_t,
        user_data: *mut c_void,
    ) -> c_int,
>;

pub type CloseCallback = Option<
    unsafe extern "C" fn(
        session: *mut nghttp2_session,
        stream_id: i32,
        error_code: u32,
        user_data: *mut c_void,
    ) -> c_int,
>;

//
// FFI functions
//
#[link(name = "nghttp2")]
unsafe extern "C" {
    pub unsafe fn nghttp2_session_callbacks_new(
        callbacks: *mut *mut nghttp2_session_callbacks,
    ) -> c_int;
    pub unsafe fn nghttp2_session_callbacks_set_send_callback2(
        callbacks: *mut nghttp2_session_callbacks,
        cb: SendCallback,
    );
    pub unsafe fn nghttp2_session_callbacks_set_on_data_chunk_recv_callback(
        callbacks: *mut nghttp2_session_callbacks,
        cb: DataCallback,
    );
    pub unsafe fn nghttp2_session_callbacks_set_on_stream_close_callback(
        callbacks: *mut nghttp2_session_callbacks,
        cb: CloseCallback,
    );

    pub unsafe fn nghttp2_session_client_new(
        session: *mut *mut nghttp2_session,
        callbacks: *mut nghttp2_session_callbacks,
        user_data: *mut c_void,
    ) -> c_int;

    // queue frames
    pub unsafe fn nghttp2_submit_settings(
        session: *mut nghttp2_session,
        flags: u8,
        iv: *const c_void,
        niv: size_t,
    ) -> c_int;
    pub unsafe fn nghttp2_submit_request2(
        session: *mut nghttp2_session,
        pri_spec: *const c_void,
        nva: *const nghttp2_nv,
        nvlen: size_t,
        data_provider: *const c_void,
        user_data: *mut c_void,
    ) -> i32;
    pub unsafe fn nghttp2_session_mem_recv2(
        session: *mut nghttp2_session,
        in_data: *const u8,
        inlen: size_t,
    ) -> size_t;

    pub unsafe fn nghttp2_session_send(session: *mut nghttp2_session) -> c_int;

    // cleanup functions
    pub unsafe fn nghttp2_session_callbacks_del(callbacks: *mut nghttp2_session_callbacks);
    pub unsafe fn nghttp2_session_terminate_session(
        session: *mut nghttp2_session,
        error_code: u32,
    ) -> c_int;
    pub unsafe fn nghttp2_session_del(session: *mut nghttp2_session);
}
