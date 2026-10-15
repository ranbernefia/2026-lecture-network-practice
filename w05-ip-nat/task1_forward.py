#!/usr/bin/env python3
"""Week 5 · Task 1 — Subnets and longest-prefix match.

Textbook §4.3.2 (IPv4 addressing, CIDR) and §4.3.3 (forwarding).

Two things a router does with every packet: work out which prefixes the
destination falls inside, and pick the longest one. The second is the whole
of "longest prefix match", and it is the reason the internet's routing table
can hold a million entries and still be answerable.

You build both, from integers up. No `ipaddress` module - that library is
exactly the thing you are supposed to understand this week.

    python3 task1_forward.py --verify
"""
import argparse

ALL_ONES = 0xFFFFFFFF   # 32비트가 전부 1인 수 (255.255.255.255)


def ip_to_int(text):
    """'10.20.30.70' -> 32비트 정수. 네 칸을 8비트씩 왼쪽으로 밀어 이어 붙인다."""
    parts = text.split(".")
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        raise ValueError(f"not an IPv4 address: {text!r}")
    n = 0
    for p in parts:
        octet = int(p)
        if octet > 255:
            raise ValueError(f"octet out of range in {text!r}")
        n = (n << 8) | octet
    return n


def int_to_ip(n):
    """32비트 정수 -> '10.20.30.70'. 8비트씩 오른쪽으로 밀면서 한 칸씩 꺼낸다."""
    return ".".join(str((n >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def prefix_mask(length):
    """프리픽스 길이 -> 서브넷 마스크 정수. 예: 24 -> 255.255.255.0 (앞 24비트만 1)"""
    return (ALL_ONES << (32 - length)) & ALL_ONES


def parse_cidr(cidr):
    """'163.152.6.0/24' -> (network as int, prefix length).

    Requirements: reject a prefix length outside 0-32, and reject an address
    whose host bits are set when they should not be (163.152.6.5/24 is a
    common way to write a host, but it is not a network).
    """
    addr_text, sep, len_text = cidr.partition("/")
    if not sep or not len_text.isdigit():
        raise ValueError(f"not a CIDR block: {cidr!r}")
    length = int(len_text)
    # R1: 프리픽스 길이는 0~32만 허용
    if not 0 <= length <= 32:
        raise ValueError(f"prefix length {length} is outside 0-32")
    addr = ip_to_int(addr_text)
    # R2: 마스크 바깥(호스트 부분)에 1이 있으면 네트워크 주소가 아니라 호스트 주소다
    if addr & ~prefix_mask(length) & ALL_ONES:
        raise ValueError(f"{cidr} has host bits set - it is a host, not a network")
    return addr, length


def network_range(cidr):
    """'163.152.6.0/24' -> (first usable, last usable, broadcast) as strings.

    Careful at the edges. /31 and /32 do not have a usable host range in the
    ordinary sense - decide what you return and say so in observation.md.
    """
    net, length = parse_cidr(cidr)
    # 브로드캐스트 = 호스트 부분을 전부 1로 채운 주소
    broadcast = net | (~prefix_mask(length) & ALL_ONES)
    if length == 32:
        # /32: 주소가 딱 하나. 그 주소 자체가 유일한 호스트이고 브로드캐스트는 없다
        return int_to_ip(net), int_to_ip(net), None
    if length == 31:
        # /31 (RFC 3021): 주소 두 개를 둘 다 호스트로 쓴다. 두 대만 잇는 연결이라 브로드캐스트가 없다
        return int_to_ip(net), int_to_ip(broadcast), None
    # 일반적인 경우: 맨 앞(네트워크 주소)과 맨 뒤(브로드캐스트)를 빼고 사이가 사용 가능
    return int_to_ip(net + 1), int_to_ip(broadcast - 1), int_to_ip(broadcast)


class ForwardingTable:
    """Longest-prefix-match forwarding.

    add(cidr, next_hop)  ·  lookup(address) -> next_hop or None

    The default route 0.0.0.0/0 matches everything and is the shortest prefix,
    so it must lose to any other match. If two entries have the same prefix
    length, the table is malformed - say what you do.
    """

    def __init__(self):
        self.routes = {}    # (네트워크 정수, 프리픽스 길이) -> 다음 홉

    def add(self, cidr, next_hop):
        key = parse_cidr(cidr)
        # 똑같은 프리픽스가 다른 다음 홉으로 또 들어오면 어느 쪽이 맞는지 알 수 없다.
        # 조용히 덮어쓰지 않고 오류로 거부한다 (같은 홉으로 다시 넣는 건 괜찮다)
        if key in self.routes and self.routes[key] != next_hop:
            raise ValueError(f"{cidr} already points to {self.routes[key]}, "
                             f"refusing to also point it to {next_hop}")
        self.routes[key] = next_hop

    def lookup(self, address):
        addr = ip_to_int(address)
        best_len, best_hop = -1, None
        # 모든 경로를 하나씩 확인한다 (빠르게 만드는 건 Task 3)
        for (net, length), hop in self.routes.items():
            # 주소에 마스크를 씌웠을 때 네트워크 주소와 같으면 이 경로에 포함된다
            if addr & prefix_mask(length) == net and length > best_len:
                # R4: 맞는 것 중 가장 긴 프리픽스를 고른다.
                # R5: 0.0.0.0/0은 길이가 0이라 다른 것이 하나라도 맞으면 자동으로 진다
                best_len, best_hop = length, hop
        return best_hop


# ------------------------------------------------------------------- harness
RANGE_CASES = [
    ("192.168.0.0/24",  "192.168.0.1",   "192.168.0.254",  "192.168.0.255"),
    ("10.0.0.0/8",      "10.0.0.1",      "10.255.255.254", "10.255.255.255"),
    ("172.16.32.0/20",  "172.16.32.1",   "172.16.47.254",  "172.16.47.255"),
    ("203.0.113.64/26", "203.0.113.65",  "203.0.113.126",  "203.0.113.127"),
]

TABLE = [
    ("0.0.0.0/0",       "default-gw"),
    ("10.0.0.0/8",      "campus"),
    ("10.20.0.0/16",    "eng-building"),
    ("10.20.30.0/24",   "lab-floor"),
    ("10.20.30.64/26",  "lab-rack-2"),
    ("192.168.1.0/24",  "home"),
]

LOOKUP_CASES = [
    ("10.20.30.70",   "lab-rack-2"),     # inside all four 10.x entries
    ("10.20.30.10",   "lab-floor"),
    ("10.20.99.1",    "eng-building"),
    ("10.99.0.1",     "campus"),
    ("8.8.8.8",       "default-gw"),
    ("192.168.1.77",  "home"),
]


def verify():
    fails = 0
    for cidr, first, last, bcast in RANGE_CASES:
        try:
            got = network_range(cidr)
        except NotImplementedError:
            print("  network_range is still a stub"); return 1
        except Exception as e:
            print(f"  FAIL  {cidr:<18} raised {e!r}"); fails += 1; continue
        ok = tuple(got) == (first, last, bcast)
        print(f"  {'ok  ' if ok else 'FAIL'}  {cidr:<18} {got}")
        fails += not ok

    t = ForwardingTable()
    try:
        for cidr, hop in TABLE:
            t.add(cidr, hop)
    except NotImplementedError:
        print("  ForwardingTable is still a stub"); return 1

    for addr, expect in LOOKUP_CASES:
        got = t.lookup(addr)
        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'}  {addr:<16} -> {got}  (want {expect})")
        fails += not ok

    print(f"\n  {len(RANGE_CASES) + len(LOOKUP_CASES) - fails}"
          f"/{len(RANGE_CASES) + len(LOOKUP_CASES)} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
