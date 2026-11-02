#!/usr/bin/env python3
"""Week 7 · Task 3 — A switch that runs out of room.

Textbook §6.4.3.

A switch does not have room for every station on the network. Its forwarding
table sits in a fixed amount of fast memory, and when that fills, something has
to go. Whatever goes gets **flooded** the next time anyone sends to it - out of
every port, to every station that did not ask for it.

`NaiveSwitch` handles a full table the simplest way: throw out whichever entry
has been there longest. That is a perfectly reasonable first idea and it is
close to the worst thing you can do with this traffic.

    python3 bench.py
    python3 bench.py --yours

Correctness first: every frame whose destination is reachable must still reach
it. A switch that floods less because it delivers less is not a switch.
"""
from collections import OrderedDict


class NaiveSwitch:
    """Correct. Evicts the oldest entry, which is not the least useful one."""

    BROADCAST = "ff:ff:ff:ff:ff:ff"

    def __init__(self, ports, capacity):
        self.ports = ports
        self.capacity = capacity
        self.table = OrderedDict()                 # mac -> port, insertion order

    def handle(self, frame, in_port):
        src, dst, now = frame
        if src not in self.table and len(self.table) >= self.capacity:
            self.table.popitem(last=False)         # throw out the oldest arrival
        self.table[src] = in_port

        if dst == self.BROADCAST or dst not in self.table:
            return [p for p in range(self.ports) if p != in_port]
        out = self.table[dst]
        return [] if out == in_port else [out]


class YourSwitch:
    """Your switch. Same interface, same deliveries, far less flooding.

        __init__(ports, capacity)
        handle((src, dst, time), in_port) -> ports to forward out of

    `self.table` must exist and must never hold more than `capacity` entries.
    The harness checks this after every frame.

    What the baseline gets wrong: it decides what to keep by **when the entry
    arrived**, and that has nothing to do with whether it is about to be needed.
    On this trace a handful of stations carry most of the traffic, and the
    baseline keeps throwing them out to make room for stations that spoke once.

    Two questions worth separating:

      * which entry should leave when the table is full?
      * should learning a new source ever be *declined*?

    The second one is less obvious and is worth thinking about before you
    dismiss it.

    Note what you are NOT allowed to do: you cannot look at `where`, you cannot
    see the future, and you cannot hold more than `capacity` entries. Everything
    you know comes from the frames you have already handled.
    """

    BROADCAST = "ff:ff:ff:ff:ff:ff"

    # 방법: 표에 있는 주소마다 "최근에 몇 번 찾아졌나"를 세고, 적게 찾아진 주소부터 내보낸다.
    # 표 밖의 주소는 아무것도 기억하지 않는다. 그래서 기억하는 주소는 언제나 capacity개 이하다.
    # 찾아진 횟수만 세므로, 가짜 주소를 보내기만 해서는 횟수가 올라가지 않는다.

    HALF_LIFE = 2048    # 이만큼 찾을 때마다 횟수를 절반으로 줄여서 옛날 인기가 사라지게 한다

    def __init__(self, ports, capacity):
        self.ports = ports
        self.capacity = capacity
        self.table = {}     # mac -> port
        self.hits = {}      # mac -> 최근에 찾아진 횟수 (표에 있는 주소만)
        self.seen = 0       # 마지막으로 절반으로 줄인 뒤 찾은 횟수

    def _learn(self, src, in_port):
        if src in self.table:
            self.table[src] = in_port       # 장비가 옮겼으면 새 포트를 믿는다
        elif len(self.table) < self.capacity:
            self.table[src] = in_port
            self.hits[src] = 0
        else:
            # 표가 꽉 찼을 때 최근에 찾아지지 않은 주소가 있을 때만 교체한다.
            # 모두 찾아지고 있으면 새 주소의 학습을 거절한다 (플러딩으로 전달은 된다)
            victim = min(self.hits, key=self.hits.get)
            if self.hits[victim] == 0:
                del self.table[victim], self.hits[victim]
                self.table[src] = in_port
                self.hits[src] = 0

    def handle(self, frame, in_port):
        src, dst, _ = frame
        self._learn(src, in_port)

        if dst == self.BROADCAST or dst not in self.table:
            return [p for p in range(self.ports) if p != in_port]
        self.hits[dst] += 1
        self.seen += 1
        if self.seen >= self.HALF_LIFE:
            self.hits = {mac: n // 2 for mac, n in self.hits.items()}
            self.seen = 0
        out = self.table[dst]
        return [] if out == in_port else [out]
