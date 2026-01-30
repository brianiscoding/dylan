from typing import List, Tuple
from urllib.parse import urlparse
import socket
import sys
import json
from pathlib import Path
import constants as c


def get_config():
    if len(sys.argv) != 2:
        print(f"ERROR: no json")
        sys.exit(1)

    f = Path(sys.argv[1])
    if not f.is_file():
        print(f"ERROR: file")
        sys.exit(1)

    with f.open("r", encoding="utf-8") as f:
        return json.load(f)


def create_pf(ip: str, port: int, loss_in: float, loss_out) -> None:
    content = (
        f'blocked_ip="{ip}"\n'
        f'blocked_port="{port}"\n'
        f'loss_in="{loss_in}"\n'
        f'loss_out="{loss_out}"\n'
        "block in proto tcp from $blocked_ip to any probability $loss_in\n"
        "block out proto tcp from any to $blocked_ip port $blocked_port probability $loss_out\n"
    )

    with open("pf.conf", "w") as f:
        f.write(content)


def update_config(cfg, updates) -> None:
    cfg.update(updates)
    f = Path(sys.argv[1])
    with f.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def main() -> None:
    cfg = get_config()
    parsed = urlparse(cfg["url"])
    if parsed.scheme not in c.SCHEME_MAP:
        return
    port: int = c.SCHEME_MAP[parsed.scheme]
    infos: List[Tuple] = socket.getaddrinfo(parsed.netloc, None)
    ip: str = list({info[4][0] for info in infos})[0]
    host: str = parsed.netloc
    path: str = parsed.path

    create_pf(ip, port, cfg["loss_in"], cfg["loss_out"])
    updates = {
        "scheme": parsed.scheme,
        "host": host,
        "path": path if path else "/",
        "port": port,
    }
    update_config(cfg, updates)


if __name__ == "__main__":
    main()

# "url": "https://www.catan.com",
# "url": "https://www.toyota.com",
# "url": "https://nghttp2.org",
# "url": "https://nghttp2.org/httpbin",
# "url": "http://nghttp2.org/httpbin",
# "url": "https://nghttp2.org/httpbin",
