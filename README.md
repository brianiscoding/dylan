# HTTP/2 Client with Packet Filter Configuration

An HTTP/2 client implementation using nghttp2 library with ctypes bindings, integrated with macOS packet filter (PF) configuration for network testing and manipulation.

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

- `client.py` - HTTP/2 client implementation with nghttp2 bindings
- `bindings.py` - ctypes bindings for nghttp2 library
- `configure.py` - Updates PF configuration with target host/port
- `config.py` - Configuration file for URL and probability settings
- `constants.py` - Constants for URL scheme mappings
- `pf.conf` - Packet filter configuration file
- `run.sh` - Convenience script to run the client

## Configuration

Edit `config.py` to set your target URL and packet filter probabilities:

```python
url = "https://nghttp2.org"
loss_in = 0.3   # Probability for incoming packet blocking
loss_out = 0.34 # Probability for outgoing packet blocking
```

## Running

### Basic Usage

Run the HTTP/2 client:

```bash
python3 client.py
```

Or use the convenience script:

```bash
./run.sh
```

### With Configuration Setup

To configure PF rules based on the URL in config.py:

```bash
./configure.py
```

This will:

1. Resolve the hostname to an IP address
2. Extract the port from the URL scheme
3. Update `pf.conf` with the IP, port, and probability values
4. Update `config.py` with the resolved host and port

### Loading PF Rules

To load the PF configuration (requires sudo):

```bash
sudo pfctl -f pf.conf
```

To view active PF rules:

```bash
sudo pfctl -sr
```

To flush all PF rules:

```bash
sudo pfctl -F all
```

## API Usage

The client module exports a single public function:

```python
from client import client

# Make an HTTP/2 GET request
client(host="nghttp2.org", port=443, scheme="https", silent_=False)
```

Parameters:

- `host` (str): Target hostname or IP address
- `port` (int): Target port (80 for HTTP, 443 for HTTPS)
- `scheme` (str): URL scheme ("http" or "https")
- `silent_` (bool): If True, suppress response output (default: False)

## How It Works

1. **HTTP/2 Client**: Establishes a connection using sockets, negotiates HTTP/2 via ALPN for HTTPS connections, and sends GET requests using the nghttp2 library
2. **PF Integration**: Configures macOS packet filter to simulate network conditions by probabilistically blocking packets to/from the target
3. **Configuration Management**: Automatically resolves hostnames and updates both PF rules and Python config

## Notes

- The packet filter features require macOS and administrative privileges
- PF configuration is useful for testing application behavior under unreliable network conditions
- **Testing Limitations**: Some websites may not be suitable for testing:
  - Sites that don't support HTTP/2 will fail to connect (HTTP/2 ALPN negotiation required)
  - Many sites implement bot detection and rate limiting that may block automated connections
  - CDN-protected sites may reject connections that don't include proper user-agent headers or cookies
  - For reliable testing, use dedicated HTTP/2 test servers like `nghttp2.org` or `www.catan.com`
