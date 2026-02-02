from typing import List, Dict, Any
from urllib.parse import urlparse
import socket
import sys
import json
from pathlib import Path
import constants as c
import ipaddress


def get_config() -> Dict[str, Any]:
    """
    Get configuration from a JSON file specified as a command-line argument.
    """
    if len(sys.argv) != 2:
        raise Exception("Wrong usage.")

    f = Path(sys.argv[1])
    if not f.is_file():
        raise Exception("No such file.")

    with f.open("r", encoding="utf-8") as f:
        return json.load(f)


def create_pf(
    ips: Dict[str, List[str]], port: int, loss_in: float, loss_out: float
) -> None:
    """
    Create a pf.conf file to block traffic to/from the specified IP and port with given loss probabilities.
    """
    content = f'loss_in="{loss_in}"\nloss_out="{loss_out}"\n'
    for ip in ips["ipv4"]:
        content += f"block in proto tcp from {ip} to any probability $loss_in\n"
        content += (
            f"block out proto tcp from any to {ip} port {port} probability $loss_out\n"
        )
    for ip in ips["ipv6"]:
        content += f"block in inet6 proto tcp from {ip} to any probability $loss_in\n"
        content += f"block out inet6 proto tcp from any to {ip} port {port} probability $loss_out\n"

    with open("pf.conf", "w") as f:
        f.write(content)


def get_ips(host: str) -> Dict[str, List[str]]:
    """
    Get IPv4 and IPv6 addresses for the specified host.
    """
    infos = socket.getaddrinfo(host, None)
    ips = {"ipv4": set(), "ipv6": set()}

    for info in infos:
        ip = info[4][0]
        if isinstance(ipaddress.ip_address(ip), ipaddress.IPv4Address):
            ips["ipv4"].add(ip)
        elif isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address):
            ips["ipv6"].add(ip)
        # raise exception for other types?
    return {k: list(v) for k, v in ips.items()}


def main() -> None:
    cfg = get_config()
    parsed = urlparse(cfg["url"])
    if parsed.scheme not in c.PORT_BY_SCHEME:
        raise Exception(f"Unsupported scheme: {parsed.scheme}.")
    ips = get_ips(parsed.netloc)
    port = c.PORT_BY_SCHEME[parsed.scheme]
    create_pf(ips, port, cfg["loss_in"], cfg["loss_out"])


if __name__ == "__main__":
    main()

"""
    "url": "https://www.catan.com",
    "url": "https://www.toyota.com",
    "url": "https://nghttp2.org",
    "url": "https://nghttp2.org/httpbin",
    "url": "http://nghttp2.org/httpbin",
    "url": "https://nghttp2.org/httpbin",
"""
