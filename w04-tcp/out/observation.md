# 4주차 · 관찰 기록

# Task 1

Q. Which protocol you chose, and the one case that forced the choice

답장(ACK)을 기다리지 않고 최대 16개를 미리 보내는 슬라이딩 윈도우 방식인 Go-Back-N을 골랐다.
stop-and-wait은 답장이 올 때까지 송신자가 놀고 있어야 해서 느리기 때문이다. 실제로 윈도우를
1로 줄여 비교해 보니 seed 246에서 2455스텝 vs 1642스텝으로 Go-Back-N이 약 1.5배 빨랐다.

Q. How many packets did the channel actually carry for 2,000 bytes of data? Compare with the minimum.

최소 250개(8바이트씩)면 되는데 실제로는 1,114개를 보내 약 4.5배가 들었다. Go-Back-N은 하나만 빠져도
그 뒤에 보낸 것까지 통째로 다시 보내기 때문이다.

Q. What broke first: loss, reordering, or duplication?

손실이다. 하나씩만 켜고 돌려 보니 중복만 켜거나 순서 뒤바뀜만 켜면 재전송 없이 딱 250개로 끝났지만
손실만 켜도 733개로 늘었다. 순서 뒤바뀜은 혼자서는 문제가 없었지만 손실로 재전송이 몰릴 때
피해를 키웠다(5개 seed 평균 773개 → 1,051개).

# Task 2

Q. The two initial sequence numbers, and why they are not zero

`out/tcp.pcapng`의 1번(SYN), 2번(SYN-ACK), 3번(ACK)이 handshake이고 ISN은 내 컴퓨터 1595265699, 서버
169970255로 연결할 때마다 달랐다. 0부터 시작하면 예전 연결의 늦게 온 패킷과 헷갈리고 다른 사람이 번호를 맞혀서
가짜 패킷을 끼워 넣기 쉬워서 무작위로 정한다.

Q. The scaled receive window, and what actually limited the transfer instead

SYN 옵션은 MSS 1460, SACK 허용이었고 window scale이 없어서(Windows 수신 윈도우 자동 조정이 꺼져 있음)
수신 윈도우는 약 64KB로 고정됐다. 유선은 RTT 한 번에 약 61KB가 도착해 64KB를 거의 꽉 채워 윈도우가
한계였고, 테더링은 RTT가 두 배로 흔들려도 속도가 그대로라 휴대폰 회선 속도가 한계였다.

Q. Your two medians, the spread, and the mechanism from B5

유선은 68.9Mbps(편차 26%, 핸드셰이크 25.0ms), 테더링은 13.7Mbps(편차 12%, 53.5ms)였다.
유선은 윈도우가 고정이라 RTT가 조금만 흔들려도 속도가 같이 흔들려서 편차가 더 컸다.
TCP는 RTT마다 보내는 양을 늘리는데(슬로 스타트), 테더링은 RTT가 두 배 길어서 속도도 늦게 올랐다.

# Task 3

Q. The baseline has the highest goodput here. Why is it still the worst sender?

baseline은 goodput이 986.8로 가장 높지만 큐를 늘 꽉 채운 채(평균 8.8) 보낸 것의 37.4%를 버리고 2,340번이나
재전송했다. 같은 링크를 쓰는 다른 사람들은 그 큐 뒤에서 기다려야해서 혼자 빠른 대신 링크 전체를 망가뜨린다.

Q. What your window converges to, and how that number relates to the link

윈도우는 20에서 멈춘다. 링크는 슬롯마다 1개씩 보내고 RTT가 20슬롯이라 20개면 링크가 쉬지않고 꽉 찬다.
19개면 빈자리가 생겨 94%로 느려졌고 25개는 속도는 같은데 큐에 줄만 길어졌다.

Q. What happened to goodput when you made the backoff gentler, and what it cost

손실이 날 때까지 늘리는 방식으로 따로 실험해 보니, 절반이 아니라 0.92배만 줄이면 goodput은 약 2%
올랐지만 손실은 8%에서 26%로 세 배가 됐다. 조금 빨라지려고 훨씬 많이 버리는 셈이라 손실을 기다리지 않고
20에서 멈추게 만들었다.
