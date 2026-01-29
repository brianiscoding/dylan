from typing import List, Tuple
from urllib.parse import urlparse
import socket
import re

import constants as c
import config as config


def update_pf(ip: str, port: int) -> None:
    with open("pf.conf", "r") as f:
        content = f.read()

    content = re.sub(r'blocked_ip="[^"]*"', f'blocked_ip="{ip}"', content)
    content = re.sub(r'blocked_port="[^"]*"', f'blocked_port="{port}"', content)
    content = re.sub(r'loss_in="[^"]*"', f'loss_in="{config.loss_in}"', content)
    content = re.sub(r'loss_out="[^"]*"', f'loss_out="{config.loss_out}"', content)

    with open("pf.conf", "w") as f:
        f.write(content)


def update_config(host: str, port: int, scheme: str) -> None:
    with open("config.py", "r") as f:
        content = f.read()

    content = re.sub(r"port = .*", f"port = {port}", content)
    content = re.sub(r"host = .*", f'host = "{host}"', content)
    content = re.sub(r"scheme = .*", f'scheme = "{scheme}"', content)

    with open("config.py", "w") as f:
        f.write(content)


def main() -> None:
    parsed = urlparse(config.url)
    if parsed.scheme not in c.SCHEME_MAP:
        return
    port: int = c.SCHEME_MAP[parsed.scheme]
    infos: List[Tuple] = socket.getaddrinfo(parsed.netloc, None)
    ip: str = list({info[4][0] for info in infos})[0]
    host: str = parsed.netloc

    update_pf(ip, port)
    update_config(host, port, parsed.scheme)


if __name__ == "__main__":
    main()
