mod bindings;

use rustls::pki_types::ServerName;
use rustls::{ClientConfig, ClientConnection, RootCertStore, StreamOwned};
use std::collections::HashMap;
use std::ffi::CString;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::sync::Arc;
use std::time::{Duration, Instant};
use url::Url;

const BUFFER_SIZE: usize = 8192;
const TIMEOUT: u64 = 10;
const NGHTTP2_NO_ERROR: u32 = 0;
const NGHTTP2_FLAG_NONE: u8 = 0;
const NGHTTP2_NV_FLAG_NONE: u8 = 0;

enum Socket {
    Tcp(TcpStream),
    Tls(StreamOwned<ClientConnection, TcpStream>),
}

impl Read for Socket {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
        match self {
            Socket::Tcp(s) => s.read(buf),
            Socket::Tls(s) => s.read(buf),
        }
    }
}

impl Write for Socket {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        match self {
            Socket::Tcp(s) => s.write(buf),
            Socket::Tls(s) => s.write(buf),
        }
    }

    fn flush(&mut self) -> std::io::Result<()> {
        match self {
            Socket::Tcp(s) => s.flush(),
            Socket::Tls(s) => s.flush(),
        }
    }
}

pub struct HTTP2Client {
    pub url: String,
    pub scheme: String,
    pub host: String,
    pub path: String,
    pub port: u16,

    pub data: Option<String>,
    pub time: Option<f64>,

    sock: Option<Socket>,
    session: Option<*mut bindings::nghttp2_session>,
    is_closed_by_stream_id: HashMap<u8, bool>,
    raw_data: Vec<u8>,
}

impl HTTP2Client {
    pub fn new(url: &str) -> Self {
        let (scheme, host, path, port) = Self::parse_url(url);

        let mut client = HTTP2Client {
            url: url.to_string(),
            scheme: scheme,
            host: host,
            path: path,
            port: port,

            data: None,
            time: None,

            sock: None,
            session: None,
            is_closed_by_stream_id: HashMap::new(),
            raw_data: Vec::new(),
        };

        client.create_socket();
        client.create_session();
        client.send_headers();
        client.get();
        client.cleanup();
        client
    }

    fn parse_url(url: &str) -> (String, String, String, u16) {
        let parsed = Url::parse(url).unwrap();

        let scheme = parsed.scheme().to_string();
        let host = parsed
            .host_str()
            .expect("URL must contain host.")
            .to_string();
        let path = parsed.path().to_string();
        let port = parsed
            .port_or_known_default()
            .expect("Unknown default port.") as u16;

        (scheme, host, path, port)
    }

    fn create_socket(&mut self) {
        match self.scheme.as_str() {
            "https" => {
                let mut roots = RootCertStore::empty();
                for cert in rustls_native_certs::load_native_certs().unwrap() {
                    roots.add(cert).unwrap();
                }
                let mut config = ClientConfig::builder()
                    .with_root_certificates(roots)
                    .with_no_client_auth();
                config.alpn_protocols = vec![b"h2".to_vec()];

                let server_name = ServerName::try_from(self.host.clone()).unwrap(); // takes ownership
                let conn = ClientConnection::new(Arc::new(config), server_name).unwrap();

                let tcp = TcpStream::connect((self.host.as_str(), self.port)).unwrap();
                let mut tls_stream = StreamOwned::new(conn, tcp);
                tls_stream.flush().unwrap();

                if tls_stream.conn.alpn_protocol() != Some(b"h2".as_ref()) {
                    panic!("ALPN negotiation failed for TLS.");
                }

                self.sock = Some(Socket::Tls(tls_stream));
            }
            "http" => {
                let tcp_stream = TcpStream::connect((self.host.as_str(), self.port)).unwrap();
                self.sock = Some(Socket::Tcp(tcp_stream));
            }
            _ => {
                panic!("Unsupported scheme: {}", self.scheme);
            }
        }
    }

    fn create_session(&mut self) {
        unsafe extern "C" fn send_cb(
            _session: *mut bindings::nghttp2_session,
            data: *const u8,
            length: libc::size_t,
            _flags: libc::c_int,
            user_data: *mut libc::c_void,
        ) -> libc::size_t {
            unsafe {
                let client: &mut HTTP2Client = &mut *(user_data as *mut HTTP2Client);
                let slice = std::slice::from_raw_parts(data, length);
                client.sock.as_mut().unwrap().write_all(slice).unwrap();
            }
            length
        }

        unsafe extern "C" fn data_cb(
            _session: *mut bindings::nghttp2_session,
            _flags: u8,
            stream_id: i32,
            data: *const u8,
            length: libc::size_t,
            user_data: *mut libc::c_void,
        ) -> libc::c_int {
            unsafe {
                let client: &mut HTTP2Client = &mut *(user_data as *mut HTTP2Client);
                client
                    .is_closed_by_stream_id
                    .entry(stream_id as u8)
                    .or_insert(false);

                let slice = std::slice::from_raw_parts(data, length);
                client.raw_data.extend_from_slice(slice);
            }
            0
        }

        unsafe extern "C" fn close_cb(
            _session: *mut bindings::nghttp2_session,
            stream_id: i32,
            _error_code: u32,
            user_data: *mut libc::c_void,
        ) -> libc::c_int {
            unsafe {
                let client: &mut HTTP2Client = &mut *(user_data as *mut HTTP2Client);
                if let Some(v) = client.is_closed_by_stream_id.get_mut(&(stream_id as u8)) {
                    *v = true;
                }
            }
            0
        }

        let mut callbacks: *mut bindings::nghttp2_session_callbacks = std::ptr::null_mut();
        unsafe {
            bindings::nghttp2_session_callbacks_new(&mut callbacks);
            bindings::nghttp2_session_callbacks_set_send_callback2(callbacks, Some(send_cb));
            bindings::nghttp2_session_callbacks_set_on_data_chunk_recv_callback(
                callbacks,
                Some(data_cb),
            );
            bindings::nghttp2_session_callbacks_set_on_stream_close_callback(
                callbacks,
                Some(close_cb),
            );
        }

        self.session = Some(std::ptr::null_mut());
        let user_data = self as *mut HTTP2Client as *mut libc::c_void;
        unsafe {
            bindings::nghttp2_session_client_new(
                self.session.as_mut().unwrap(),
                callbacks,
                user_data,
            );
            bindings::nghttp2_session_callbacks_del(callbacks);
        }
    }

    fn create_name_value(
        &self,
        name: &str,
        value: &str,
    ) -> (bindings::nghttp2_nv, CString, CString) {
        let name_cstr = CString::new(name).unwrap();
        let value_cstr = CString::new(value).unwrap();

        let nv = bindings::nghttp2_nv {
            name: name_cstr.as_ptr() as *mut u8,
            namelen: name.len() as libc::size_t,
            value: value_cstr.as_ptr() as *mut u8,
            valuelen: value.len() as libc::size_t,
            flags: NGHTTP2_NV_FLAG_NONE,
        };

        (nv, name_cstr, value_cstr)
    }

    fn send_headers(&mut self) {
        let mut storage: Vec<CString> = Vec::new();
        let mut headers = Vec::new();

        for (n, v) in [
            (":method", "GET"),
            (":scheme", self.scheme.as_str()),
            (":authority", self.host.as_str()),
            (":path", self.path.as_str()),
        ] {
            let (nv, name_c, value_c) = self.create_name_value(n, v);
            headers.push(nv);
            storage.push(name_c);
            storage.push(value_c);
        }

        unsafe {
            bindings::nghttp2_submit_settings(
                self.session.unwrap(),
                NGHTTP2_FLAG_NONE,
                std::ptr::null(),
                0,
            );
            bindings::nghttp2_submit_request2(
                self.session.unwrap(),
                std::ptr::null(),
                headers.as_ptr(),
                headers.len(),
                std::ptr::null(),
                std::ptr::null_mut(),
            );
            bindings::nghttp2_session_send(self.session.unwrap());
        }
    }

    fn get(&mut self) {
        let end = Instant::now() + Duration::from_secs(TIMEOUT);
        let mut buf = [0u8; BUFFER_SIZE];
        let sock = self.sock.as_mut().unwrap();
        let session = self.session.unwrap();

        while Instant::now() < end {
            let all_closed = !self.is_closed_by_stream_id.is_empty()
                && self.is_closed_by_stream_id.values().all(|&v| v);
            if all_closed {
                self.data = Some(String::from_utf8_lossy(&self.raw_data).into_owned());
                return;
            }

            let n = match sock.read(&mut buf) {
                Ok(0) => continue,
                Ok(n) => n,
                Err(_) => continue,
            };

            unsafe {
                bindings::nghttp2_session_mem_recv2(session, buf.as_ptr(), n);
                bindings::nghttp2_session_send(session);
            }
        }

        panic!("Timeout exceeded.");
    }

    fn cleanup(&mut self) {
        if let Some(session) = self.session.take() {
            unsafe {
                bindings::nghttp2_session_terminate_session(session, NGHTTP2_NO_ERROR);
                bindings::nghttp2_session_send(session);
                bindings::nghttp2_session_del(session);
            }
        }

        self.raw_data.clear();
    }
}

fn main() {
    let client = HTTP2Client::new("https://nghttp2.org");
    // let client = HTTP2Client::new("http://nghttp2.org");

    println!("{}", client.data.as_ref().unwrap());
}
