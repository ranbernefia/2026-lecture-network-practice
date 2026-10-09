#!/usr/bin/env python3
"""Week 4 · Task 3 — Beat the fixed window.

Textbook §3.7.

`FixedWindow` is a sender that never adapts. It picks a window and keeps it,
forever, no matter what the network says back. It is not a strawman: it is what
you get if you skip congestion control entirely, and it was the internet's
actual failure mode in October 1986.

Write `YourControl` and beat it on the harness:

    python3 bench.py
    python3 bench.py --yours

The interface is two events and one number:

    .window        how many packets you are willing to have in flight
    .on_ack()      one packet made it there and back
    .on_loss()     a packet was dropped, or timed out waiting for its ACK

That is all the information a real TCP sender has. It cannot see the queue,
it cannot see the link rate, and neither can you. You infer them from these
two events, which is the entire idea of §3.7.
"""


class FixedWindow:
    """Send 64 packets at a time and never listen."""

    def __init__(self):
        self.window = 64

    def on_ack(self):
        pass

    def on_loss(self):
        pass


class YourControl:
    """Your congestion control.

    Things worth knowing before you start:

    * The link drains one packet per slot and the round trip is 20 slots, so
      the pipe holds about 20 packets. Above that you are only filling a queue.
    * The queue is 10 packets deep and drops from the tail. Filling it does not
      make you faster - it makes you slower, and everybody behind you too.
    * Cutting hard on every loss costs you throughput. Not cutting costs you
      correctness. §3.7 is the argument about where between those to sit.
    * You are allowed to grow differently before and after your first loss.
      That distinction has a name in the textbook.
    """

    # 목표 윈도우 = 파이프 크기(1패킷/슬롯 × RTT 20슬롯 = 20패킷).
    # 20개면 링크가 쉬지 않고 꽉 차고, 그보다 많이 보내면 속도는 그대로인데 큐에 줄만 길어진다.
    TARGET = 20

    def __init__(self):
        self.window = 1.0
        self.cooldown = 0       # 줄인 직후 이만큼의 ACK 동안은 손실이 와도 또 줄이지 않음

    def on_ack(self):
        if self.cooldown > 0:
            self.cooldown -= 1
        # 슬로 스타트: ACK 하나마다 +1 (RTT마다 2배). 목표에 닿으면 더 늘리지 않고 유지한다
        if self.window < self.TARGET:
            self.window = min(self.window + 1, self.TARGET)

    def on_loss(self):
        # 큐가 넘치면 한 번에 여러 개가 버려져 손실 알림이 연달아 온다. 첫 번째에만 반응한다
        if self.cooldown > 0:
            return
        # 손실 = 큐가 넘쳤다는 신호. 윈도우를 절반으로 줄이고, 다시 슬로 스타트로 목표까지 올라간다
        self.window = max(self.window / 2, 1)
        self.cooldown = int(self.window)
