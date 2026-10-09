#!/usr/bin/env python3
"""Week 4 · Task 1 — Build reliable delivery on top of an unreliable channel.

Textbook §3.4 (reliable data transfer) and §3.5 (TCP's sequence numbers).

`UnreliableChannel` below loses packets, reorders them, duplicates them, and
delays them. It is the network as §3.4 models it. Your job is to move a file
across it and have the bytes arrive intact and in order.

That is the whole of TCP's reliability story with the congestion control taken
out, and it is worth building once by hand before you ever trust a socket again.

    python3 task1_rdt.py --verify
"""
import argparse, hashlib, random

PAYLOAD = 8            # bytes per packet - small, so you see the sequencing


class UnreliableChannel:
    """Loses 10%, duplicates 3%, reorders, and delays. Deterministic by seed.

    You may not make it nicer. You may not read its internals. It is the only
    way your sender can reach your receiver.
    """

    def __init__(self, seed=246, loss=0.10, dup=0.03, reorder=0.10):
        self.rng = random.Random(seed)
        self.loss, self.dup, self.reorder = loss, dup, reorder
        self.wire = []          # packets in flight, in no particular order
        self.stats = {"sent": 0, "lost": 0, "duplicated": 0, "delivered": 0}

    def send(self, packet):
        """Hand a packet to the network. It may never come out."""
        self.stats["sent"] += 1
        if self.rng.random() < self.loss:
            self.stats["lost"] += 1
            return
        copies = 2 if self.rng.random() < self.dup else 1
        self.stats["duplicated"] += copies - 1
        for _ in range(copies):
            if self.rng.random() < self.reorder and self.wire:
                self.wire.insert(self.rng.randrange(len(self.wire)), packet)
            else:
                self.wire.append(packet)

    def receive(self):
        """Take the next packet out, or None if the network has nothing."""
        if not self.wire:
            return None
        self.stats["delivered"] += 1
        return self.wire.pop(0)


class Sender:
    """송신자 — Go-Back-N 방식의 슬라이딩 윈도우 (누적 ACK 사용).

    한 번에 최대 WINDOW개의 패킷을 답장(ACK) 없이 미리 보내 둔다.
    ACK 번호 k는 "0 ~ k-1번까지 순서대로 다 받았으니, 다음엔 k번을 줘"라는 뜻이다.

    중복 ACK 처리(R3): 채널이 옛날 ACK를 늦게 또는 두 번 배달할 수 있다.
    이미 알고 있는 것보다 작거나 같은 번호의 ACK는 그냥 무시한다.
    그래서 오래된 ACK 때문에 진행 상황(base)이 뒤로 돌아가는 일이 없다.
    """

    WINDOW = 16     # 답장 없이 동시에 보내 둘 수 있는 최대 패킷 수
    TIMEOUT = 30    # 이만큼의 시간(tick) 동안 진전이 없으면 윈도우 전체를 다시 보냄

    def __init__(self, data_channel, ack_channel, data):
        self.data_channel = data_channel
        self.ack_channel = ack_channel
        # R1: 데이터를 PAYLOAD(8바이트)씩 잘라 둔다. 리스트의 위치(0, 1, 2, ...)가 곧 번호(seq)
        self.chunks = [data[i:i + PAYLOAD] for i in range(0, len(data), PAYLOAD)]
        self.n = len(self.chunks)   # 보내야 할 패킷의 총 개수 (2000바이트면 250개)
        self.base = 0          # 아직 ACK를 못 받은 것 중 가장 앞 번호
        self.next_seq = 0      # 다음에 처음으로 보낼 번호
        self.sent_at = {}      # 번호 -> 마지막으로 보낸 시각(tick). 타임아웃 계산에 사용
        self.tick = 0          # step()이 한 번 불릴 때마다 1씩 늘어나는 시계

    def _send(self, seq):
        # 패킷에 번호(seq)와 내용(payload)을 함께 담아 보낸다 (R1)
        self.data_channel.send({"seq": seq, "payload": self.chunks[seq]})
        self.sent_at[seq] = self.tick

    def step(self):
        """Do one unit of work. Return False when you believe you are done."""
        self.tick += 1

        # 1) 도착한 ACK 확인. 지금보다 큰 번호일 때만 앞으로 전진한다 (중복/옛날 ACK 무시, R3)
        ack = self.ack_channel.receive()
        if ack is not None and ack["ack"] > self.base:
            self.base = ack["ack"]

        # 2) 모든 패킷이 ACK를 받았으면 끝 (R6)
        if self.base >= self.n:
            return False

        # 3) 윈도우에 빈자리가 있으면 새 패킷을 하나 보낸다
        if self.next_seq < self.base + self.WINDOW and self.next_seq < self.n:
            self._send(self.next_seq)
            self.next_seq += 1
        # 4) 윈도우가 꽉 찼는데 가장 앞 패킷(base)이 TIMEOUT 넘게 ACK를 못 받았다면,
        #    잃어버린 것으로 보고 base부터 보낸 것 전부를 다시 보낸다 (R4, "Go-Back-N")
        else:
            oldest = self.sent_at.get(self.base)
            if oldest is None or self.tick - oldest >= self.TIMEOUT:
                for seq in range(self.base, self.next_seq):
                    self._send(seq)

        return True


class Receiver:
    """수신자 — 지금 기다리는 바로 그 번호의 패킷만 받고, 나머지는 버린다.

    순서 보장(R2): 번호가 건너뛴 패킷(예: 3번을 기다리는데 5번이 옴)은 저장하지 않는다.
    어차피 송신자가 타임아웃 후 3번부터 다시 보내 주므로, 결과는 항상 0, 1, 2, ... 순서가 된다.

    중복 데이터 처리(R3): 이미 받은 번호가 또 오면 저장하지 않는다.
    그래서 같은 내용이 두 번 붙어 출력이 망가지는 일이 없다.

    무슨 패킷이 오든 "지금까지 순서대로 받은 다음 번호"를 ACK로 돌려준다.
    """

    def __init__(self, data_channel, ack_channel):
        self.data_channel = data_channel
        self.ack_channel = ack_channel
        self.expected = 0       # 다음에 받아야 할 번호
        self.chunks = {}        # 번호 -> 내용. expected보다 작은 번호만 들어 있음

    def step(self):
        pkt = self.data_channel.receive()
        if pkt is not None:
            # 기다리던 번호면 저장하고 다음 번호를 기다린다
            if pkt["seq"] == self.expected:
                self.chunks[self.expected] = pkt["payload"]
                self.expected += 1
            # 번호가 expected보다 작음 -> 이미 받은 것의 중복. 버림 (R3)
            # 번호가 expected보다 큼 -> 순서가 뒤바뀌어 먼저 온 것. 버림 (R2)
            # 어느 경우든 "다음엔 expected번을 줘"라고 ACK를 보낸다
            self.ack_channel.send({"ack": self.expected})
        return True

    def data(self):
        """The bytes reassembled so far."""
        return b"".join(self.chunks[i] for i in range(self.expected))


# ------------------------------------------------------------------- harness
def verify(seed=246, size=2000, max_steps=200_000):
    original = bytes(random.Random(seed).getrandbits(8) for _ in range(size))
    up, down = UnreliableChannel(seed), UnreliableChannel(seed + 1)

    # Data goes out over `up`, ACKs come back over `down`. Both are unreliable.
    sender = Sender(up, down, original)
    receiver = Receiver(up, down)

    for _ in range(max_steps):
        alive = sender.step()
        receiver.step()
        if not alive and len(receiver.data() or b"") >= size:
            break

    got = receiver.data() or b""
    ok = hashlib.sha256(got).hexdigest() == hashlib.sha256(original).hexdigest()
    print(f"  bytes    sent {size}   received {len(got)}")
    print(f"  channel  {up.stats}")
    print(f"  result   {'IDENTICAL' if ok else 'CORRUPTED OR INCOMPLETE'}")
    return 0 if ok else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    p.add_argument("--seed", type=int, default=246)
    a = p.parse_args()
    raise SystemExit(verify(a.seed) if a.verify else p.print_help())
