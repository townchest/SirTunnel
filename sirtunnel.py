#!/usr/bin/env python3

import sys
import json
import time
from urllib import request
from pathlib import Path
import argparse
from typing import Dict, Any, Optional


def get_server_name_on_port_443(servers: Dict[str, Any]) -> Optional[str]:
    """Find the server listening on port 443."""
    for server, config in servers.items():
        if ":443" in config.get("listen", []):
            return server
    return None


def fetch_servers(get_servers_url: str) -> Dict[str, Any]:
    """Fetch the list of servers from the Caddy API."""
    try:
        req = request.Request(method="GET", url=get_servers_url)
        response = request.urlopen(req)
        response_data = response.read().decode('utf-8')
        return json.loads(response_data)
    except Exception as e:
        print(f"Error fetching servers: {e}")
        sys.exit(1)


def create_tunnel(create_url: str, headers: Dict[str, str], body: bytes) -> None:
    """Create a tunnel using the Caddy API."""
    try:
        req = request.Request(method="POST", url=create_url, headers=headers)
        request.urlopen(req, body)
        print("Tunnel created successfully")
    except Exception as e:
        print(f"Error creating tunnel: {e}")
        sys.exit(1)


def delete_tunnel(delete_url: str) -> None:
    """Delete the tunnel using the Caddy API."""
    try:
        req = request.Request(method="DELETE", url=delete_url)
        request.urlopen(req)
    except Exception as e:
        print(f"Error deleting tunnel: {e}")


def log_tunnel_creation(log_path: Path, host: str, port: str) -> None:
    """Log the tunnel creation details."""
    with open(log_path, "a+", encoding="utf-8") as logfile:
        logfile.write(f"{host}\t\t{port}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a tunnel using Caddy server.")
    parser.add_argument("host", help="Host for the tunnel")
    parser.add_argument("port", help="Port for the tunnel")
    args = parser.parse_args()

    host = args.host
    port = args.port
    tunnel_id = f"{host}-{port}"

    log_path = Path(__file__).with_name("log.txt").absolute()
    log_tunnel_creation(log_path, host, port)

    caddy_add_route_request = {
        "@id": tunnel_id,
        "match": [{"host": [host]}],
        "handle": [{"handler": "reverse_proxy", "upstreams": [{"dial": f":{port}"}]}],
    }

    body = json.dumps(caddy_add_route_request).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    get_servers_url = "http://127.0.0.1:2019/config/apps/http/servers"
    response_json = fetch_servers(get_servers_url)

    srv_name = get_server_name_on_port_443(response_json)
    if not srv_name:
        print("No server found listening on port 443")
        sys.exit(1)

    create_url = f"http://127.0.0.1:2019/config/apps/http/servers/{srv_name}/routes"
    create_tunnel(create_url, headers, body)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Cleaning up tunnel")
        delete_url = f"http://127.0.0.1:2019/id/{tunnel_id}"
        delete_tunnel(delete_url)


if __name__ == "__main__":
    main()