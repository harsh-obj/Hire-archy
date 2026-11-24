"""
Custom Django `runserver` command for Hire-archy.

- Opens the server to the local network by default (`0.0.0.0`).
- Scans and displays all available ports when starting.
- Automatically selects an available port if the requested port is busy or
  blocked by Windows port exclusions / permissions.
- Prints both localhost and LAN IPv4 URLs for easy device access.
"""

import os
import socket
from typing import List

from django.contrib.staticfiles.management.commands.runserver import Command as StaticFilesRunserverCommand

COMMON_DEV_PORTS = [
    8000, 8001, 8002, 8003, 8004,
    8080, 8081, 8088, 8888,
    3000, 3001, 5000, 5001, 9000, 9001,
]


def is_port_available(addr: str, port: int) -> bool:
    """Return True if `port` can be bound cleanly without permission or conflict errors."""
    probe_host = "127.0.0.1" if addr in ("0.0.0.0", "0", "::", "") else addr

    # 1. Check if a service is already actively listening on the port
    check_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    check_sock.settimeout(0.05)
    try:
        if check_sock.connect_ex((probe_host, port)) == 0:
            return False
    except OSError:
        pass
    finally:
        check_sock.close()

    # 2. Attempt an exclusive bind to catch Windows EACCES / excluded port ranges
    bind_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            bind_sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        bind_sock.bind(("0.0.0.0" if addr in ("0.0.0.0", "0", "") else addr, port))
        return True
    except OSError:
        return False
    finally:
        bind_sock.close()


def find_available_ports(addr: str, requested_port: int) -> List[int]:
    """Scan common ports plus ports adjacent to `requested_port` and return available ones."""
    candidates = list(COMMON_DEV_PORTS)
    for offset in range(0, 6):
        p = requested_port + offset
        if 1024 <= p <= 65535 and p not in candidates:
            candidates.append(p)
    seen = []
    for port in sorted(set(candidates)):
        if is_port_available(addr, port):
            seen.append(port)
    return seen


def get_lan_ips() -> List[str]:
    """Discover non-loopback IPv4 addresses on the local network."""
    ips: List[str] = []

    # Primary outbound interface IP (no packets are actually sent over UDP)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udp.connect(("10.255.255.255", 1))
        ip = udp.getsockname()[0]
        if ip and not ip.startswith("127."):
            ips.append(ip)
    except OSError:
        pass
    finally:
        udp.close()

    try:
        _, _, addr_list = socket.gethostbyname_ex(socket.gethostname())
        for ip in addr_list:
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass

    return ips


class Command(StaticFilesRunserverCommand):
    help = "Starts Hire-archy development server open to the local network and displays available ports."
    default_addr = "0.0.0.0"
    default_port = "8000"

    def handle(self, *args, **options):
        # Parse address and port via parent logic first
        self._resolved_available_ports: List[int] = []
        super().handle(*args, **options)

    def run(self, **options):
        requested_port = int(self.port)
        is_reloader_child = os.environ.get("RUN_MAIN") == "true"

        if is_reloader_child and os.environ.get("HIREARCHY_SELECTED_PORT"):
            self.port = os.environ["HIREARCHY_SELECTED_PORT"]
            raw_avail = os.environ.get("HIREARCHY_AVAILABLE_PORTS", "")
            self._resolved_available_ports = [int(x) for x in raw_avail.split(",") if x.isdigit()]
        else:
            available_ports = find_available_ports(self.addr, requested_port)
            self._resolved_available_ports = available_ports

            if not is_port_available(self.addr, requested_port):
                self.stdout.write(
                    self.style.WARNING(
                        f"\n[Port Notice] Requested port {requested_port} is unavailable or blocked on this system."
                    )
                )
                if available_ports:
                    fallback_port = available_ports[0]
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[Port Notice] Automatically switching to available port {fallback_port}."
                        )
                    )
                    self.port = str(fallback_port)
                else:
                    self.stderr.write(
                        self.style.ERROR("[Port Notice] No common free ports were found in scan range.")
                    )

            os.environ["HIREARCHY_SELECTED_PORT"] = str(self.port)
            os.environ["HIREARCHY_AVAILABLE_PORTS"] = ",".join(str(p) for p in available_ports)

        super().run(**options)

    def on_bind(self, server_port):
        super().on_bind(server_port)

        avail = getattr(self, "_resolved_available_ports", [])
        if not avail and os.environ.get("HIREARCHY_AVAILABLE_PORTS"):
            avail = [int(x) for x in os.environ["HIREARCHY_AVAILABLE_PORTS"].split(",") if x.isdigit()]

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Local URL:   http://127.0.0.1:{server_port}/"))
        if self.addr in ("0.0.0.0", "0", "::"):
            lan_ips = get_lan_ips()
            if lan_ips:
                for ip in lan_ips:
                    self.stdout.write(self.style.SUCCESS(f"Network URL: http://{ip}:{server_port}/"))
            else:
                self.stdout.write(self.style.NOTICE("Network URL: Bound to 0.0.0.0 (no active LAN IPv4 detected)"))

        if avail:
            ports_str = ", ".join(str(p) for p in avail)
            self.stdout.write(self.style.HTTP_INFO(f"Available ports on this machine: {ports_str}"))
        self.stdout.write("")
        self.stdout.flush()
