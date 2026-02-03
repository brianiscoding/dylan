# HTTP/2 Client with Packet Filter Network Simulation

HTTP/2 client implementations for testing network resilience with simulated packet loss via macOS packet filter (PF).

## Implementations

### Python Version (`client.py`, `configure_pf.py`)

HTTP/2 client using nghttp2 C library via ctypes FFI bindings. Resolves hostnames, generates PF rules, and simulates packet loss.

**Quick Start:**

```bash
./scripts/run.sh
```

**Manual:**

```bash
python3 ./configure_pf.py config.json
sudo pfctl -f pf.conf
python3 ./client.py "https://example.com"
```

**Config** (`config.json`):

```json
{
  "url": "https://httpbin.org/bytes/10000000",
  "verbose": true,
  "loss_in": 0.3,
  "loss_out": 0.2
}
```

### Rust Version (`ru/`)

Equivalent implementation in Rust using rustls for TLS and native nghttp2 bindings. See `ru/README.md` or `ru/Cargo.toml` for details.

**Build:** `cargo build -C ru --release`
**Run:** `./ru/target/release/ru "https://example.com"`

## Requirements

- macOS (for PF)
- **Python**: Python 3.7+, nghttp2 library, jq, coreutils
  ```bash
  brew install nghttp2 jq coreutils
  ```
- **Rust**: Cargo, nghttp2 development files
  ```bash
  brew install nghttp2
  cargo build -C ru --release
  ```

## Configuration Fields

| Field      | Type    | Range   | Description                      |
| ---------- | ------- | ------- | -------------------------------- |
| `url`      | string  | -       | HTTP/2 URL to fetch              |
| `verbose`  | boolean | -       | Display response                 |
| `loss_in`  | float   | 0.0–1.0 | Incoming packet loss probability |
| `loss_out` | float   | 0.0–1.0 | Outgoing packet loss probability |

## How It Works

1. **resolve**: Hostname → IPv4/IPv6 addresses
2. **configure**: Generate `pf.conf` with blocking rules
3. **load**: `sudo pfctl -f pf.conf`
4. **fetch**: HTTP/2 GET request (with packet loss)
5. **cleanup**: Remove PF rules

## Troubleshooting

- **ALPN failed**: Target doesn't support HTTP/2. Try `https://nghttp2.org`
- **Permission denied**: Script needs sudo for pfctl. Password will be prompted.
- **Connection failed**: Check `ping <hostname>` and firewall rules
- **Timeout**: Reduce packet loss or test with closer server
