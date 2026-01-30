# HTTP/2 Client with Packet Filter Configuration

An HTTP/2 client implementation using nghttp2 library with ctypes bindings, integrated with macOS packet filter (PF) configuration for network testing and packet loss simulation.

## Features

- **HTTP/2 Client**: Full HTTP/2 support via nghttp2 library with automatic ALPN negotiation
- **Packet Filter Integration**: Configure macOS PF to simulate packet loss for testing network resilience
- **Flexible Configuration**: JSON-based configuration for easy setup and management
- **Verbose Mode**: Optional detailed output for debugging and inspection

## Dependencies

### System Requirements

- **macOS** (for PF configuration features)
- **Python 3.7+**
- **nghttp2** library

### Installing nghttp2

Using Homebrew:

```bash
brew install nghttp2
```

## Project Structure

```
.
├── client.py           # HTTP/2 client class implementation
├── bindings.py         # ctypes bindings for nghttp2 library
├── configure.py        # Configuration management and PF setup
├── constants.py        # Constants for URL schemes, buffer sizes, etc.
├── config.json         # Configuration file (URL, port, packet loss settings, etc.)
├── pf.conf             # Generated packet filter rules (auto-created)
├── scripts/
│   ├── run.sh         # Main execution script
│   └── clean.sh       # Cleanup script
└── README.md          # This file
```

## Configuration

Edit `config.json` to customize your HTTP/2 client settings:

```json
{
  "url": "https://nghttp2.org",
  "verbose": true,
  "loss_in": 0.4,
  "loss_out": 0
}
```

### Configuration Fields

- **url**: Target URL to fetch (scheme, host, and path are extracted from this)
- **verbose**: Enable verbose output (true/false)
- **loss_in**: Probability for incoming packet blocking (0.0 - 1.0)
- **loss_out**: Probability for outgoing packet blocking (0.0 - 1.0)

## Running

### Quick Start

Execute the main script which handles everything:

```bash
./scripts/run.sh
```

This will:

1. Check for nghttp2 installation (installs via Homebrew if missing)
2. Run configure.py to update configuration and generate PF rules
3. Load PF rules (requires sudo, will prompt for password)
4. Execute the HTTP/2 client
5. Display active PF rules
6. Run cleanup script

### Manual Steps

If you prefer to run components separately:

```bash
# Update configuration and generate PF rules
python3 configure.py config.json

# Load PF rules (requires sudo)
sudo pfctl -f pf.conf

# Run the HTTP/2 client
python3 client.py "https://nghttp2.org"

# With verbose output
python3 client.py "https://nghttp2.org" --verbose

# View active PF rules
sudo pfctl -vvsr

# Flush PF rules
sudo pfctl -F all
```

## API Usage

### HTTP2Client Class

```python
from client import HTTP2Client

# Create and run a client
client = HTTP2Client(
    url="https/nghttp2.org",
    verbose=True
)
```

## How It Works

### 1. Configuration Management (configure.py)

- Reads `config.json`
- Resolves hostname to IP address
- Generates `pf.conf` with packet filter rules

### 2. HTTP/2 Client (client.py)

- Accepts a URL as command-line argument
- Parses URL to extract scheme, host, path, and port
- Creates socket connection (raw for HTTP, SSL/TLS for HTTPS)
- Negotiates HTTP/2 via ALPN for HTTPS connections
- Sends GET request headers using nghttp2
- Receives and displays response (if verbose mode enabled)
- Gracefully closes session and connection

### 3. Packet Filter Integration

- PF rules are generated to simulate network conditions
- `loss_in`: Probabilistically blocks incoming TCP packets from the target
- `loss_out`: Probabilistically blocks outgoing TCP packets to the target
- Useful for testing application behavior under unreliable network conditions

## Testing Limitations

Some websites may not be suitable for testing:

- Sites that don't support HTTP/2 will fail to connect
- Many sites implement bot detection and rate limiting that may block automated connections
- CDN-protected sites may reject connections without proper headers
- **Recommended test servers**: `nghttp2.org` or similar HTTP/2 testing services

## Troubleshooting

### Permission Denied on PF Rules

- The script requires sudo to load PF rules
- You'll be prompted for your password when running `./scripts/run.sh`

### nghttp2 Not Found

- The script will automatically attempt to install nghttp2 via Homebrew
- Manual installation: `brew install nghttp2`

### Connection Failed

- Verify the target URL is reachable: `curl -I <url>`
- Check that the target supports HTTP/2 (especially for HTTPS)
- Ensure no local firewall is blocking the connection

### Verbose Output Not Showing

- Set `"verbose": true` in `config.json`
- Run with `--verbose` flag: `python3 client.py "<url>" --verbose`

## Dependencies in Detail

- **nghttp2**: C library for HTTP/2 protocol
