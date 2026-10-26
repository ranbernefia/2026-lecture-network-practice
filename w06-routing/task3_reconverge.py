#!/usr/bin/env python3
"""Week 6 · Task 3 — Reconverge without recomputing the world.

Textbook §5.2.1, §5.3.

A link flaps. Every router in the area has to decide what changed. `FullRecompute`
does the honest thing: throw the table away and run Dijkstra again, from scratch,
for every event. It is correct and it is what the first implementations did.

It is also why a single flapping link in a large area used to melt the CPU of
every router that could see it.

Beat it:

    python3 bench.py
    python3 bench.py --yours

Correctness first. `bench.py` compares your table against a full recompute after
**every single event**. A router that is fast and wrong black-holes traffic.
"""
import heapq

# The harness counts how many times you run a full SPF. This is the score:
# wall-clock time in Python says more about dictionary overhead than about
# routing, but "how many times did the CPU have to recompute the world" is
# exactly what melted real routers.
SPF_RUNS = 0


def dijkstra_table(graph, source):
    """Reference shortest-path-first. Returns {destination: first_hop}.

    Use THIS function whenever you need a full recompute. Rolling your own to
    dodge the counter is not an optimisation, it is cheating the meter.
    """
    global SPF_RUNS
    SPF_RUNS += 1
    best = {source: (0, None)}
    pq, done = [(0, source, None)], set()
    while pq:
        cost, node, first_hop = heapq.heappop(pq)
        if node in done:
            continue
        done.add(node)
        best[node] = (cost, first_hop)
        for nbr, w in sorted(graph[node].items()):
            if nbr in done:
                continue
            hop = nbr if node == source else first_hop
            if cost + w < best.get(nbr, (float("inf"), None))[0]:
                best[nbr] = (cost + w, hop)
                heapq.heappush(pq, (cost + w, nbr, hop))
    return {d: h for d, (_, h) in best.items() if d != source and h}


class FullRecompute:
    """On every event, forget everything and run SPF again."""

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source
        self.table = dijkstra_table(self.graph, source)

    def link_change(self, a, b, cost):
        """cost=None means the link went down."""
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost
        self.table = dijkstra_table(self.graph, self.source)


class YourRouter:
    """Your router. Same two methods, same table, less work per event.

    What is actually true after one link changes:

      * most destinations are not affected at all
      * a link that is not on any of your shortest paths, going *up*, can only
        matter if it creates something shorter
      * a link going *down* only matters if you were using it

    Deciding which of those applies, cheaply, without getting it wrong, is the
    task. Getting it wrong is worse than being slow - the harness will catch it
    on the event where it happens.
    """

    # 이벤트 사이에 기억해 두는 것 (표 말고 추가로):
    #   dist[n]   = source에서 n까지의 최단 거리
    #   parent[n] = 최단 경로에서 n 바로 앞의 노드 (최단 경로 "나무"의 부모)
    # 이 둘이 있으면 "이 선이 바뀌면 영향이 있나?"를 전체 계산 없이 판단할 수 있다.

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source
        self._recompute()

    def _recompute(self):
        # 전체 다시 계산. 표는 반드시 dijkstra_table로 만든다(횟수가 세어진다).
        # 거리와 부모는 같은 순간에 같은 그래프로 같이 계산해 둔다.
        self.table = dijkstra_table(self.graph, self.source)
        self.dist, self.parent = _tree(self.graph, self.source)

    def link_change(self, a, b, cost):
        """cost=None means the link went down."""
        old = self.graph[a].get(b)
        if cost == old:
            return                          # 이미 끊겨 있거나 비용이 그대로: 할 일 없음
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost

        # 경우 1·2: 선이 끊기거나 비싸짐 -> 최단 경로 나무에 쓰던 선일 때만 영향이 있다
        if old is not None and (cost is None or cost > old):
            for p, y in ((a, b), (b, a)):
                if self.parent.get(y) == p and not self._reroute_same_cost(y):
                    self._recompute()
            return                          # 안 쓰던 선이면 거리도 표도 그대로

        # 경우 3: 선이 생기거나 싸짐 -> 저장해 둔 거리로 "더 짧은 길이 생기나?"만 확인
        for x, y in ((a, b), (b, a)):
            if x not in self.dist:
                continue                    # x에 갈 수 없으면 이 방향으로는 새 길이 없다
            new = self.dist[x] + cost
            if y not in self.dist or new < self.dist[y]:
                self._shorten(y, new)       # 더 짧은 길이 생김 -> 거리가 줄어드는 노드만 고친다
                return
            if new == self.dist[y] and y != self.source:
                # 비용이 같은 길이 하나 더 생김. 기준 계산은 "먼저 확정된 앞 노드" 쪽 길을 고른다.
                p = self.parent[y]
                if (self.dist[x], x) < (self.dist[p], p):
                    hop = y if x == self.source else self.table[x]
                    if hop != self.table[y]:
                        self._recompute()   # 나가는 이웃이 바뀜 -> 전체 계산
                        return
                    self.parent[y] = x      # 나가는 이웃은 같으니 부모만 바꿔 두면 된다

    def _shorten(self, y, new):
        """y까지 더 짧은 길(거리 new)이 생겼을 때, 거리가 줄어드는 노드만 찾아 고친다.

        거리는 줄어들 수만 있으므로 y에서 시작해 "더 짧아지는 이웃"만 따라 퍼져 나가면 된다.
        더 짧아지지 않는 곳에서 멈추므로, 영향받지 않는 대부분의 노드는 건드리지 않는다.
        """
        dist = self.dist
        dist[y] = new
        heap, changed = [(new, y)], set()
        while heap:
            d, n = heapq.heappop(heap)
            if d != dist[n]:
                continue
            changed.add(n)
            for nbr, w in self.graph[n].items():
                if d + w < dist.get(nbr, float("inf")):
                    dist[nbr] = d + w
                    heapq.heappush(heap, (d + w, nbr))
        # 부모가 바뀔 수 있는 노드: 거리가 바뀐 노드와 그 이웃들
        region = set(changed)
        for n in changed:
            region.update(q for q in self.graph[n] if q in dist)
        region.discard(self.source)
        for n in region:
            self.parent[n] = min((dist[q], q) for q, w in self.graph[n].items()
                                 if q in dist and dist[q] + w == dist[n])[1]
        self._refresh_hops(region)

    def _refresh_hops(self, nodes):
        """nodes와 그 아래 가지(자손)의 "나가는 이웃"을 부모를 따라 다시 정한다."""
        children = {}
        for n, par in self.parent.items():
            children.setdefault(par, []).append(n)
        todo, stack = set(), list(nodes)
        while stack:
            n = stack.pop()
            if n not in todo:
                todo.add(n)
                stack.extend(children.get(n, []))
        # 거리가 가까운 노드부터: 부모의 이웃이 먼저 정해져 있어야 자식이 물려받을 수 있다
        for n in sorted(todo, key=lambda n: (self.dist[n], n)):
            par = self.parent[n]
            self.table[n] = n if par == self.source else self.table[par]

    def _reroute_same_cost(self, y):
        """y로 가던 나무의 선이 사라졌을 때, 같은 거리로 y에 가는 다른 앞 노드가 있으면
        전체 계산 없이 고친다. 고쳤으면 True, 전체 계산이 필요하면 False.

        같은 거리의 다른 길이 있으면 어느 노드의 거리도 바뀌지 않는다. 바뀌는 건 y의 부모와,
        y 아래 가지(자손)들이 물려받는 "나가는 이웃"뿐이다.
        """
        d = self.dist[y]
        # 기준 계산과 같은 규칙: 같은 거리면 먼저 확정되는 (거리, 이름)이 작은 앞 노드를 고른다
        cands = [(self.dist[q], q) for q, w in self.graph[y].items()
                 if q in self.dist and self.dist[q] + w == d]
        if not cands:
            return False                    # 다른 길이 없다 -> 거리가 늘어나므로 전체 계산
        self.parent[y] = min(cands)[1]
        self._refresh_hops([y])             # y와 그 아래 가지의 나가는 이웃만 다시 정한다
        return True


def _tree(graph, source):
    """dijkstra_table과 똑같은 순서로 계산하면서 거리와 부모를 기록한다.

    YourRouter._recompute에서 dijkstra_table을 부를 때만 함께 쓴다. 그래서 전체 계산을
    한 횟수는 계량기(SPF_RUNS)에 찍힌 숫자와 같다.
    """
    best = {source: (0, None)}
    pq, done = [(0, source, None)], set()
    dist, parent = {}, {}
    while pq:
        cost, node, prev = heapq.heappop(pq)
        if node in done:
            continue
        done.add(node)
        dist[node], parent[node] = cost, prev
        for nbr, w in sorted(graph[node].items()):
            if nbr in done:
                continue
            if cost + w < best.get(nbr, (float("inf"), None))[0]:
                best[nbr] = (cost + w, node)
                heapq.heappush(pq, (cost + w, nbr, node))
    return dist, parent
