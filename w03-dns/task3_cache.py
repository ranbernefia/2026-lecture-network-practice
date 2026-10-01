#!/usr/bin/env python3
"""3주차 · Task 3 — baseline 캐시보다 잘 만들기.

교재 §2.4.2 (캐싱), §2.4.3 (TTL).

`BaselineCache`는 작동은 하지만 여러 군데가 잘못됐고, 그중 하나는 느린 것보다 더 심각하다.
문제를 찾아 `YourCache`를 작성하고, 하네스로 개선을 증명한다:

    python3 bench.py                 # baseline만
    python3 bench.py --yours         # baseline vs 내 캐시, 나란히 비교

규칙
----
* `bench.py`는 수정하지 않는다.
* `YourCache`는 `BaselineCache`와 같은 두 메서드를 제공해야 한다.
* 속도만 보는 게 아니다 - TTL이 만료된 레코드를 내준 **stale 답변**도 센다.
  전부 영원히 캐싱하면 아주 빠르지만 완전히 틀린 캐시가 된다.

목표
----
baseline 성적: **upstream 325회, hit rate 67.5%, stale 266건**.

  pass   : stale 0
  good   : stale 0, upstream이 baseline 이하
  strong : 위 조건 + observation.md에 "이 워크로드에서 올바른 캐시가 낼 수 있는
           최소 upstream 횟수는 얼마고, 왜 그 아래로는 못 가는지" 적기
"""
import time


class BaselineCache:
    """누군가 급하게 짠 DNS 캐시.

    캐싱은 하지만, 정확하지도 빠르지도 않다.
    """

    FIXED_LIFETIME = 60          # TTL과 상관없이 무조건 60초 동안 보관

    def __init__(self, upstream):
        self.upstream = upstream  # upstream(name) -> (address, ttl)
        self.entries = []         # [name, address, stored_at] 리스트

    def lookup(self, name, now):
        """`name`의 주소를 반환하되, 필요할 때만 upstream에 물어본다."""
        for entry in self.entries:                      # 선형 탐색
            if entry[0] == name:
                if now - entry[2] < self.FIXED_LIFETIME:
                    return entry[1]
                self.entries.remove(entry)
                break
        address, ttl = self.upstream(name)
        self.entries.append([name, address, now])
        return address

    def stats(self):
        return {"entries": len(self.entries)}


class YourCache:
    """내가 만든 캐시.

    인터페이스는 동일: __init__(upstream), lookup(name, now) -> address, stats().
    `upstream(name)`은 네트워크 왕복 비용이 들고 (address, ttl)을 반환한다.
    이 ttl은 authoritative 서버가 실제로 보낸 값인데, baseline은 이걸 버린다.

    baseline의 두 버그는 원인이 하나다: 실제 TTL을 무시하고 고정 60초를 쓴다는 것.

      - 정확성 버그: TTL이 60초보다 짧은 이름(예: www.microsoft.com, 20초)은
        1분 내내 캐싱되어 그중 40초는 만료된 채로 응답됨 - stale 답변.
      - 성능 버그: TTL이 60초보다 긴 이름(예: www.korea.ac.kr, 3600초)은
        아직 멀쩡한데도 60초 만에 버려져서 불필요한 upstream 조회가 발생.

    각 레코드의 실제 TTL을 지키면 둘 다 해결된다: 이름 -> (address, expires_at)을
    저장하는 dict. now < expires_at일 때만 hit이고, 아니면 miss로 다시 조회한다.
    """

    def __init__(self, upstream):
        self.upstream = upstream
        self.entries = {}          # name -> (address, expires_at)
        self.hits = 0
        self.misses = 0

    def lookup(self, name, now):
        entry = self.entries.get(name)
        if entry is not None:
            address, expires_at = entry
            if now < expires_at:
                self.hits += 1
                return address
        self.misses += 1
        address, ttl = self.upstream(name)
        self.entries[name] = (address, now + ttl)
        return address

    def stats(self):
        return {"entries": len(self.entries), "hits": self.hits, "misses": self.misses}
