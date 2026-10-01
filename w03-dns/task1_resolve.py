#!/usr/bin/env python3
"""3주차 · Task 1 — 반복적 리졸버 만들기.

교재 §2.4.2 - §2.4.3.

`dig +trace`가 대신 해주는 root -> TLD -> authoritative 위임 추적을 직접 코드로 구현한다.
`dig`를 셸에서 불러도 되고 `dnspython`을 써도 된다 - 핵심은 위임을 직접 따라가는 것.

    python3 task1_resolve.py www.korea.ac.kr
    python3 task1_resolve.py --verify        # dig와 비교 검증
"""
import argparse, shutil, subprocess, sys

import dns.exception
import dns.flags
import dns.message
import dns.query
import dns.rdatatype
import dns.resolver

TIMEOUT = 3.0             # 요청당 타임아웃(초)
MAX_HOPS = 30             # 전체 조회 횟수 상한 (glue 없는 서버 찾기도 포함)
MAX_CNAME_REDIRECTS = 8   # CNAME 재시작 최대 허용 횟수


class ResolutionError(Exception):
    pass

# root 서버들. 모든 탐색은 여기서 시작한다.
ROOT_SERVERS = [
    "198.41.0.4",       # a.root-servers.net
    "199.9.14.201",     # b.root-servers.net
    "192.33.4.12",      # c.root-servers.net
]

# (이름, 종류). "stable"은 dig와 정확히 일치해야 하고,
# "cdn"은 CDN이라 매번 다른 주소가 나올 수 있어 답만 받으면 통과.
VERIFY_NAMES = [
    ("www.korea.ac.kr", "stable"),
    ("dns.google", "stable"),
    ("en.wikipedia.org", "stable"),
    ("www.stanford.edu", "stable"),
    ("www.microsoft.com", "cdn"),
]


class Resolver:
    """반복적 리졸버.

    서버에게 대신 찾아달라고(재귀) 부탁하지 않고, 위임을 직접 따라간다.
    처리해야 할 것: glue 없는 위임, 무응답 서버, CNAME 재시작, 무한루프 방지.
    """

    def resolve(self, name):
        path = []
        budget = [0]                    # 공유 카운터 - 몇 번 물어봤는지
        address = self._resolve(name, path, budget, cname_chain=frozenset())
        return address, path

    def _resolve(self, name, path, budget, cname_chain):
        """root부터 `name`을 찾는 한 번의 탐색.
        CNAME이면 재시작하고, glue 없는 네임서버는 자기 자신을 다시 불러 찾는다.
        path와 budget을 모든 호출이 공유해서, 전체 탐색 기준으로 깊이를 제한한다.
        """
        name = name.rstrip(".") + "."
        norm = name.rstrip(".").lower()
        if norm in cname_chain:
            raise ResolutionError(f"CNAME loop back to {name}")
        if len(cname_chain) >= MAX_CNAME_REDIRECTS:
            raise ResolutionError(f"too many CNAME redirects resolving {name}")
        cname_chain = cname_chain | {norm}

        servers = list(ROOT_SERVERS)
        while True:
            budget[0] += 1
            if budget[0] > MAX_HOPS:
                raise ResolutionError(f"hop budget ({MAX_HOPS}) exceeded resolving {name}")

            resp = self._ask_first(servers, name, path)
            if resp is None:
                raise ResolutionError(f"no server answered for {name} (tried {servers})")

            address, cname_target = self._read_answer(resp, name)
            if address:
                return address
            if cname_target:
                return self._resolve(cname_target, path, budget, cname_chain)

            ns_names, glue = self._read_delegation(resp)
            if not ns_names:
                raise ResolutionError(
                    f"dead end for {name}: no answer and no delegation from {path[-1]}")

            next_servers = []
            for ns in ns_names:
                if ns in glue:
                    next_servers.extend(glue[ns])
                else:
                    # glue 없음 - 이 네임서버 이름을 먼저 root부터 따로 찾아야 함
                    try:
                        next_servers.append(self._resolve(ns, path, budget, cname_chain))
                    except ResolutionError:
                        continue          # 이 NS는 실패 - 위임 안의 다음 NS 시도
            if not next_servers:
                raise ResolutionError(f"delegation for {name} had no reachable nameserver")
            servers = next_servers

    @staticmethod
    def _ask_first(servers, name, path):
        """서버 목록을 순서대로 물어보다가 응답하는 곳이 나오면 반환. (+norecurse)"""
        query = dns.message.make_query(name, dns.rdatatype.A)
        query.flags = 0                  # RD 플래그 끔 - 재귀 요청 안 함
        for server in servers:
            path.append(server)
            try:
                resp = dns.query.udp(query, server, timeout=TIMEOUT)
                if resp.flags & dns.flags.TC:
                    resp = dns.query.tcp(query, server, timeout=TIMEOUT)
            except (dns.exception.Timeout, OSError, dns.exception.DNSException):
                continue                 # 이 서버는 응답 없음 - 다음 서버로
            return resp
        return None

    @staticmethod
    def _read_answer(resp, name):
        """A 레코드가 있으면 반환하고, CNAME만 있으면 그 대상 이름을 반환."""
        norm = name.rstrip(".").lower()
        cname_target = None
        for rrset in resp.answer:
            owner = rrset.name.to_text().rstrip(".").lower()
            if rrset.rdtype == dns.rdatatype.CNAME and owner == norm:
                cname_target = rrset[0].target.to_text()
            elif rrset.rdtype == dns.rdatatype.A:
                return rrset[0].address, None
        return None, cname_target

    @staticmethod
    def _read_delegation(resp):
        """authority 섹션의 NS 이름들과, additional 섹션의 glue A 레코드를 추출."""
        ns_names = [r.target.to_text()
                    for rrset in resp.authority if rrset.rdtype == dns.rdatatype.NS
                    for r in rrset]
        glue = {}
        for rrset in resp.additional:
            if rrset.rdtype == dns.rdatatype.A:
                glue.setdefault(rrset.name.to_text(), []).append(rrset[0].address)
        return ns_names, glue


# ------------------------------------------------------------------- harness
def dig_answer(name):
    """시스템 리졸버가 주는 답 (비교용). dig가 있으면 dig를, 없으면 dnspython을 사용."""
    if shutil.which("dig"):
        out = subprocess.run(["dig", "+short", name, "A"],
                             capture_output=True, text=True).stdout
        return [l for l in out.split() if l and l[0].isdigit()]
    try:
        answer = dns.resolver.resolve(name, "A", lifetime=5)
        return sorted(r.address for r in answer)
    except dns.exception.DNSException:
        return []


def verify():
    r, failures = Resolver(), 0
    for name, kind in VERIFY_NAMES:
        try:
            addr, path = r.resolve(name)
        except NotImplementedError:
            print("Nothing implemented yet - write Resolver.resolve first.")
            return 1
        except Exception as e:
            print(f"  FAIL  {name:<22} your resolver raised {e!r}")
            failures += 1
            continue
        expected = dig_answer(name)
        if addr in expected:
            note = ""
        elif kind == "cdn":
            note = "  <- differs, but this name is CDN-hosted. Explain it."
        else:
            note = "  <- should have matched"
            failures += 1
        print(f"  {'FAIL' if note.endswith('matched') else 'ok  '}  {name:<22} "
              f"you={addr:<16} dig={','.join(expected) or '-'}   "
              f"hops={len(path)}{note}")
    print(f"\n  {len(VERIFY_NAMES) - failures}/{len(VERIFY_NAMES)} ok")
    return 1 if failures else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name", nargs="?", default="www.korea.ac.kr")
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()

    if a.verify:
        sys.exit(verify())

    addr, path = Resolver().resolve(a.name)
    for i, server in enumerate(path, 1):
        print(f"  {i}. asked {server}")
    print(f"\n  {a.name} -> {addr}")


if __name__ == "__main__":
    main()
