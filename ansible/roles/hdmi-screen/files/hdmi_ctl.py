#!/usr/bin/env python3
"""Send one command to the HDMI player and print its reply (for testing and scripts).

usage: hdmi_ctl.py status | play <file> | stop | reload
"""
import json, socket, sys
SOCK = "/run/connectbox/hdmi.sock"


def send(req, sock_path=SOCK, timeout=10):
    """Send req (dict) to the player's control socket and return its reply (dict)."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(sock_path)
    s.sendall(json.dumps(req).encode() + b"\n")
    buf = b""
    while b"\n" not in buf:
        data = s.recv(65536)
        if not data:
            break
        buf += data
    s.close()
    return json.loads(buf.split(b"\n", 1)[0] or b"{}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    req = {"cmd": sys.argv[1]}
    if sys.argv[1] == "play":
        req["path"] = sys.argv[2]
    print(json.dumps(send(req)))
