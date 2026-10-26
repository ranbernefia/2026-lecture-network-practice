#!/usr/bin/env python3
"""Week 6 · Task 1 — Link state: build the forwarding table yourself.

Textbook §5.2 (link state and distance vector) and §5.3 (OSPF).

Every OSPF router ends up holding the same map of the network, and then each one
computes, alone, where to send a packet for every destination. The computation is
Dijkstra; the output is a forwarding table with **one next hop per destination**,
not a path.

That last part is what makes routing work without anybody carrying a route around
in the packet. Build it.

    python3 task1_linkstate.py --verify
"""
import argparse
import heapq

# Undirected weighted graph: node -> {neighbour: cost}
TOPOLOGY = {
    "u": {"v": 2, "w": 5, "x": 1},
    "v": {"u": 2, "w": 3, "x": 2},
    "w": {"u": 5, "v": 3, "x": 3, "y": 1, "z": 5},
    "x": {"u": 1, "v": 2, "w": 3, "y": 1},
    "y": {"w": 1, "x": 1, "z": 2},
    "z": {"w": 5, "y": 2},
}


def dijkstra(graph, source):
    """Shortest path cost from `source` to every node.

    Return {node: cost}. Unreachable nodes must not appear.

    You write the loop. `heapq` is allowed; `networkx` is not.
    """
    return {node: cost for node, (cost, _) in _shortest(graph, source).items()}


def _shortest(graph, source):
    """다익스트라 본체. {노드: (최소 비용, source에서 처음 나가는 이웃)}을 돌려준다.

    힙(heapq)에 (지금까지 비용, 첫 홉, 노드)를 넣고, 비용이 가장 작은 것부터 하나씩 확정한다.
    처음 꺼낸 순간의 비용이 그 노드까지의 최소 비용이다 (비용이 음수가 아니기 때문).

    동점 처리: 비용이 같으면 튜플의 두 번째 칸(첫 홉 이름)이 작은 것이 먼저 꺼내진다.
    즉 같은 비용의 길이 여러 개면 "이름이 알파벳순으로 앞선 이웃"으로 나가는 길을 고른다.
    """
    done = {}
    heap = [(0, None, source)]
    while heap:
        cost, hop, node = heapq.heappop(heap)
        if node in done:
            continue            # 이미 더 싸게(또는 같은 비용에 앞선 이름으로) 확정됨
        done[node] = (cost, hop)
        for nbr, w in graph.get(node, {}).items():
            if nbr not in done:
                # source를 떠나는 첫 걸음이면 그 이웃이 첫 홉, 아니면 물려받는다
                heapq.heappush(heap, (cost + w, nbr if node == source else hop, nbr))
    done.pop(source)            # 자기 자신은 빼고 돌려준다
    return done


def forwarding_table(graph, source):
    """What the router at `source` actually installs.

    Return {destination: first_hop}, where first_hop is a **direct neighbour**
    of `source` - the one interface a packet for that destination leaves by.

    The source itself is not in the table. Neither are unreachable nodes.

    The trap: it is easy to compute the full path and then take path[1]. That
    works, but think about what a router does when two shortest paths tie, and
    pick a rule. Say which in observation.md.
    """
    # 경로 전체를 저장하지 않고, 다익스트라를 돌리면서 "처음 나간 이웃"만 따라 넘겨준다.
    # 그래서 첫 홉은 항상 source의 직접 이웃이고(R3), source 자신은 들어가지 않는다(R4).
    return {node: hop for node, (_, hop) in _shortest(graph, source).items()}


def link_down(graph, a, b):
    """A copy of `graph` with the link a-b removed, in both directions."""
    g = {n: dict(e) for n, e in graph.items()}
    g[a].pop(b, None)
    g[b].pop(a, None)
    return g


# ------------------------------------------------------------------- harness
# Costs from the textbook's worked example, §5.2.1
EXPECTED_COST_U = {"v": 2, "w": 3, "x": 1, "y": 2, "z": 4}
EXPECTED_TABLE_U = {"v": "v", "w": "x", "x": "x", "y": "x", "z": "x"}


def verify():
    fails = 0
    try:
        cost = dijkstra(TOPOLOGY, "u")
    except NotImplementedError:
        print("  dijkstra is still a stub"); return 1
    ok = cost == EXPECTED_COST_U
    print(f"  {'ok  ' if ok else 'FAIL'}  costs from u: {cost}")
    if not ok:
        print(f"        expected {EXPECTED_COST_U}")
    fails += not ok

    try:
        table = forwarding_table(TOPOLOGY, "u")
    except NotImplementedError:
        print("  forwarding_table is still a stub"); return 1
    ok = table == EXPECTED_TABLE_U
    print(f"  {'ok  ' if ok else 'FAIL'}  table at u:  {table}")
    if not ok:
        print(f"        expected {EXPECTED_TABLE_U}")
    fails += not ok

    # every node should be able to reach every other
    for n in TOPOLOGY:
        t = forwarding_table(TOPOLOGY, n)
        missing = set(TOPOLOGY) - {n} - set(t)
        bad = [d for d, h in t.items() if h not in TOPOLOGY[n]]
        ok = not missing and not bad
        print(f"  {'ok  ' if ok else 'FAIL'}  table at {n} covers all, hops are neighbours"
              + (f"  missing={missing} bad={bad}" if not ok else ""))
        fails += not ok

    # cutting a link must change somebody's mind
    cut = link_down(TOPOLOGY, "u", "x")
    after = forwarding_table(cut, "u")
    ok = after != table
    print(f"  {'ok  ' if ok else 'FAIL'}  u reroutes when u-x goes down: {after}")
    fails += not ok

    print(f"\n  {'all ok' if not fails else str(fails) + ' failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
