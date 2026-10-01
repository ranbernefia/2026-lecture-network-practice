#!/usr/bin/env python3
"""3주차 · Task 2 — DNS가 정말로 사용자를 유도(steer)하는가? 직접 측정한다.

교재 §2.4.3 (레코드), §2.5 (CDN).

    python3 task2_steering.py --collect        # 원본 데이터 수집
    python3 task2_steering.py --report         # 분석 결과 작성

12개 사이트(SITES)에 대해 CNAME 체인을 끝까지 따라가고, 세 리졸버(RESOLVERS)에게 같은
이름을 물어봐서 주소가 다른지 비교한다. "서드파티인지" 판단하는 규칙은 정답이 없으니
직접 정하고, 그 규칙이 틀리는 사이트를 최소 하나 찾아서 observation.md에 설명한다.
"""
import argparse, json, os

import dns.rdatatype
import dns.resolver

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

MAX_CHAIN_HOPS = 10

SITES = [
    "www.microsoft.com",     # Akamai, 여러 홉
    "www.netflix.com",       # 자체 CDN
    "www.adobe.com",
    "www.cnn.com",
    "www.apple.com",
    "www.korea.ac.kr",       # CDN 아예 없음
    "www.stanford.edu",
    "www.bbc.co.uk",
    "www.spotify.com",
    "www.github.com",
    "www.wikipedia.org",
    "www.nytimes.com",
]

RESOLVERS = {
    "system": None,          # 이 기기의 기본 리졸버
    "google": "8.8.8.8",
    "quad9":  "9.9.9.9",
}


def query(site, server=None):
    """한 리졸버에게 `site`를 물어보고 CNAME 체인을 따라간다.

    재귀 리졸버는 체인 전체(CNAME들 + 최종 A 레코드)를 응답 하나에 다 담아서 주므로,
    홉을 보려고 추가로 질의할 필요는 없다. 반환값 (chain, addresses, error):
      chain     [site, cname1, ..., final_name]  (CNAME 없으면 [site]만)
      addresses 최종 이름의 A 레코드 목록 (정렬됨)
      error     실패 시 짧은 에러 메시지, 성공하면 None
    """
    resolver = dns.resolver.Resolver(configure=(server is None))
    if server:
        resolver.nameservers = [server]
    resolver.timeout = 3
    resolver.lifetime = 5

    try:
        answer = resolver.resolve(site, "A")
    except Exception as e:
        return [site], [], f"{type(e).__name__}: {e}"

    remaining = list(answer.response.answer)
    chain = [site.rstrip(".")]
    current = site.rstrip(".").lower()
    addresses = []
    for _ in range(MAX_CHAIN_HOPS):
        advanced = False
        for rrset in remaining:
            owner = rrset.name.to_text().rstrip(".").lower()
            if owner != current:
                continue
            if rrset.rdtype == dns.rdatatype.CNAME:
                target = rrset[0].target.to_text().rstrip(".")
                chain.append(target)
                current = target.lower()
                remaining.remove(rrset)
                advanced = True
                break
            if rrset.rdtype == dns.rdatatype.A:
                addresses = sorted(r.address for r in rrset)
        if not advanced:
            break
    return chain, addresses, None


def collect(network):
    """체인과 리졸버별 응답을 out/chains.json에 저장한다.

    chains.json은 네트워크 라벨을 최상위 키로 쓰므로, 다른 네트워크에서
    (--network campus, --network phone 등) 두 번 실행해도 덮어쓰지 않고
    둘 다 같은 파일에 쌓인다 - B3(두 네트워크 비교)에 필요한 부분.
    """
    path = os.path.join(OUT, "chains.json")
    data = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

    site_data = {}
    for site in SITES:
        print(f"  {site} ...", end=" ", flush=True)
        per_resolver = {}
        for label, server in RESOLVERS.items():
            chain, addresses, error = query(site, server)
            per_resolver[label] = {"chain": chain, "addresses": addresses, "error": error}
        site_data[site] = per_resolver
        print("ok")

    data[network] = site_data
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\n  wrote {path}  (network: {network}, now has: {', '.join(data)})")


def registrable_domain(name):
    """마지막 두 라벨 - 가장 단순한 규칙. co.kr, co.uk처럼 접미사가 두 마디인
    사이트에서는 진짜 등록 도메인이 세 마디라서 이 규칙이 틀릴 수 있다.
    """
    labels = name.rstrip(".").split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else name


def is_third_party(site, final_zone):
    """판정 규칙: 마지막 두 라벨이 다르면 서드파티."""
    return registrable_domain(site) != registrable_domain(final_zone)


# 문자열만 비교하는 규칙이 실제로 틀리는 사이트와 그 이유.
# 두 번째 도메인을 누가 소유했는지는 문자열만 봐서는 알 수 없다.
KNOWN_RULE_ERRORS = {
    "www.wikipedia.org": (
        "chain ends at wikimedia.org, a *different* registrable domain from "
        "wikipedia.org, so the two-label rule calls it third-party. But "
        "wikimedia.org is the Wikimedia Foundation's own infrastructure - "
        "the same operator as wikipedia.org, just a second domain name they "
        "also own. It is the mirror image of the netflix.com case: an "
        "organization running its own CDN, except this one happens to live "
        "under a domain that fails a same-string test. No amount of "
        "string comparison can catch this - it requires knowing who "
        "actually owns wikimedia.org."
    ),
}


def report():
    """out/chains.json을 읽어 out/report.md를 작성한다."""
    chains_path = os.path.join(OUT, "chains.json")
    with open(chains_path, encoding="utf-8") as f:
        data = json.load(f)

    networks = list(data)
    canon_net = data[networks[0]]

    rows = []
    for site in SITES:
        per_resolver = canon_net[site]
        # 표에 쓸 대표 체인/최종 zone은 system 리졸버 기준으로 잡는다.
        canon = per_resolver.get("system") or next(iter(per_resolver.values()))
        chain = canon["chain"]
        final_zone = chain[-1]
        third_party = is_third_party(site, final_zone)
        rows.append({
            "site": site,
            "chain_len": len(chain) - 1,     # site 자신은 빼고 센 CNAME 홉 수
            "final_zone": final_zone,
            "third_party": third_party,
        })
    cdn_sites = [r["site"] for r in rows if r["chain_len"] > 0]

    # 리졸버 간 비교: 같은 네트워크 안에서 리졸버끼리 답이 다른가?
    steered_by_resolver = {}
    for net in networks:
        steered = []
        for site in cdn_sites:
            sets = {label: frozenset(v["addresses"]) for label, v in data[net][site].items()
                     if v["addresses"]}
            if len(set(sets.values())) > 1:
                steered.append(site)
        steered_by_resolver[net] = steered

    # 네트워크 간 비교: 같은 리졸버로, 서로 다른 네트워크에서 비교 - 이게
    # 진짜 (b) 주장(위치 기반 유도)의 검증이다. 공개 리졸버 3개를 한 곳에서
    # 물어보는 건 사실 "그 리졸버 자신의" anycast 라우팅을 보는 것에 가깝다.
    steered_by_network = None
    if len(networks) > 1:
        steered_by_network = {}
        for label in RESOLVERS:
            hits = []
            for site in cdn_sites:
                addr_sets = set()
                for net in networks:
                    entry = data[net][site].get(label, {})
                    if entry.get("addresses"):
                        addr_sets.add(frozenset(entry["addresses"]))
                if len(addr_sets) > 1:
                    hits.append(site)
            steered_by_network[label] = hits

    lines = []
    lines.append("# Task 2 - DNS Steering Report\n")
    lines.append(f"Networks measured: {', '.join(networks)}"
                 + ("" if len(networks) > 1 else
                    "  (single vantage point - see observation.md)") + "\n")

    lines.append("## Chains and third-party classification\n")
    lines.append("| Site | Chain length | Final zone | Third party? | Rule's verdict |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        verdict = "third party" if r["third_party"] else "not third party"
        lines.append(f"| {r['site']} | {r['chain_len']} | {r['final_zone']} | "
                      f"{'yes' if r['third_party'] else 'no'} | {verdict} |")
    lines.append("")

    lines.append("## Steering number\n")
    for net in networks:
        s = steered_by_resolver[net]
        lines.append(f"- **[{net}]** {len(s)} of {len(cdn_sites)} CDN-hosted sites answered "
                     f"with a different address set to at least one of the "
                     f"{len(RESOLVERS)} resolvers ({', '.join(RESOLVERS)}): "
                     f"{', '.join(s) if s else '(none)'}.")
    if steered_by_network:
        for label, hits in steered_by_network.items():
            lines.append(f"- **[resolver={label}, across networks {', '.join(networks)}]** "
                         f"{len(hits)} of {len(cdn_sites)} sites answered differently: "
                         f"{', '.join(hits) if hits else '(none)'}.")
    else:
        lines.append("- Only one network was measured, so the location-based part of claim (b) "
                     "(same resolver, two networks) could not be tested here - only the "
                     "resolver-to-resolver comparison above. Run `--collect --network <label>` "
                     "again from a second network (e.g. phone tethering) to fill this in.")
    lines.append("")

    lines.append("## Where the rule (last two labels) is wrong\n")
    for site, why in KNOWN_RULE_ERRORS.items():
        if site in canon_net:
            lines.append(f"- `{site}` - {why}")
    lines.append("")

    report_path = os.path.join(OUT, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  wrote {report_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--collect", action="store_true")
    p.add_argument("--report", action="store_true")
    p.add_argument("--network", default="network1",
                   help="이번 측정 지점 라벨, 예: campus / phone (B3)")
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.collect:
        collect(a.network)
    elif a.report:
        report()
    else:
        p.print_help()
