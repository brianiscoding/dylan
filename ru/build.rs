fn main() {
    pkg_config::Config::new()
        .probe("libnghttp2")
        .expect("nghttp2 not found");
}
