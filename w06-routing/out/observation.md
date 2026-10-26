# 6주차 · 관찰 기록

# Task 1

Q. Your tie-breaking rule for equal-cost paths, and what a real router does

비용이 같으면 이름이 알파벳순으로 앞선 이웃으로 보냈다. 실제 라우터는 같은 비용의 길을 모두 써서 트래픽을 나눠 보낸다(ECMP).

Q. u's next hop for w, and why it is not w

x다. w로 바로 가면 비용 5, x→y→w로 돌아가면 3으로 더 싸기 때문이다.

Q. After u-x fails, which destinations changed hop and which did not

v만 그대로였고 w, x, y, z는 모두 x에서 v로 바뀌었다.

# Task 2

Q. The ocean crossing hop from A3, and the cable it suggests

중간 구간이 * * *로 가려져 구간 이름은 못 봤지만, 국내 1.1.1.1은 4ms, 미국 서버는 192ms라 그 사이에서 태평양 해저 케이블을 건넜다.

Q. Your reconvergence time, and whether it matches the hello/dead intervals in the config

세 라우터 표는 1초 안에 바뀌었지만, 선이 살아 있던 r3는 35.5초 뒤에야 r1이 없어진 걸 알았다. 설정값(Hello 10초, Dead 40초)과 맞는다.

Q. Why coming back up is not the same as going down

끊길 땐 1초 안, 복구는 7.1초였다. 복구는 다시 인사(Hello)를 주고받고 지도를 맞춰야 해서 더 걸린다.

Q. C3: why a cost change is faster than a failure

0.5초였다. 비용 변경은 바로 알리면 되지만, 고장은 먼저 알아채야 해서 최대 40초가 걸린다.

# Task 3

Q. What you keep between events, and what it costs you in memory

각 라우터까지의 최단 거리와 바로 앞 노드를 기억한다. 약 26KB가 더 든다.

Q. The three cases above: which you handle, and which event type still forces a full SPF

세 가지 다 처리한다. 쓰던 선이 끊기거나 비싸졌는데 같은 거리의 다른 길이 없을 때만 전체 계산을 한다.

Q. R5: slower in wall time, still right for a router. Why?

파이썬에서는 따지는 일이 더 걸려 느렸지만(2.2초 vs 1.8초), 라우터는 CPU가 약해서 전체 계산 횟수를 줄이는 게(1,001번 → 186번) 더 중요하다.
