#!/usr/bin/env python3
"""Week 5 · Task 3 — Make longest-prefix match fast.

Textbook §4.3.3.

`LinearTable` is correct and it is what you probably wrote in Task 1: keep the
prefixes in a list, check every one, remember the longest that matched. On six
entries that is fine. A real router holds close to a million, and it has to
answer while the packet is still in the buffer.

Beat it:

    python3 bench.py
    python3 bench.py --yours

Correctness first: `bench.py` checks every one of your answers against the
linear table. A fast router that forwards to the wrong next hop is not a
router, it is an outage.
"""


class LinearTable:
    """Correct, and slow in the obvious way."""

    def __init__(self):
        self.entries = []                     # (prefix_len, network, next_hop)

    def add(self, network, prefix_len, next_hop):
        self.entries.append((prefix_len, network, next_hop))

    def lookup(self, address):
        best = None
        for plen, net, hop in self.entries:
            mask = (0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF
            if address & mask == net and (best is None or plen > best[0]):
                best = (plen, hop)
        return best[1] if best else None


class YourTable:
    """Your table. Same three methods, same answers, fewer comparisons.

    Addresses and networks are plain 32-bit ints here - no strings, no parsing,
    so that the benchmark measures your lookup and nothing else.

    Two directions worth knowing about before you pick one:

      * group by prefix length. There are only 33 possible lengths, and you can
        ask them in an order that lets you stop early.
      * walk the address one bit at a time. Each bit takes you to at most one
        child, so the work is bounded by the address width, not by the table size.

    The second is what hardware does. The first is easier and often enough.
    Say which you chose and what it cost you in memory.
    """

    # 방법: 프리픽스 길이별로 묶기.
    # /24는 /24끼리, /16은 /16끼리 사전(dict)에 넣어 둔다. 사전은 "이 네트워크 있어?"를
    # 항목 수와 상관없이 한 번에 찾아 준다. 찾을 때는 긴 길이부터 물어보고 처음 맞는 곳에서 멈춘다.

    def __init__(self):
        self.by_len = {}        # 프리픽스 길이 -> {네트워크 정수: 다음 홉}
        self.order = []         # 찾을 순서: [(마스크, 그 길이의 사전), ...] 긴 길이부터

    def add(self, network, prefix_len, next_hop):
        group = self.by_len.setdefault(prefix_len, {})
        # 같은 길이·같은 네트워크가 또 오면 먼저 넣은 것을 유지한다 (LinearTable과 같은 답)
        group.setdefault(network, next_hop)
        # 새 길이가 생길 때만 찾을 순서를 다시 만든다 (길이는 최대 33가지)
        if len(group) == 1:
            self.order = [((0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF, self.by_len[plen])
                          for plen in sorted(self.by_len, reverse=True)]

    def lookup(self, address):
        # 긴 길이부터: 주소에 그 길이의 마스크를 씌워 사전에 있는지 본다.
        # 처음 맞는 것이 가장 긴 프리픽스이므로 바로 돌려준다.
        for mask, group in self.order:
            hop = group.get(address & mask)
            if hop is not None:
                return hop
        return None
