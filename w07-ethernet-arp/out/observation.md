# 7주차 · 관찰 기록

# Task 1

Q. Why must a frame never go back out of the port it came in on? Give the concrete thing that breaks if it does

보낸 장비가 자기 프레임을 다시 받게 되고, 스위치 두 대가 연결된 곳에서는 프레임이 둘 사이를 계속 오가며 회선을 채운다.

Q. A switch floods when it does not know. A router drops. Why the difference?

스위치는 모르는 주소도 일단 다 보내면 도착하고 답장에서 위치를 배운다. 라우터는 인터넷 전체에 뿌릴 수 없고 표도 저절로 배워지지 않아서 길이 없으면 버린다.

Q. Your aging is a timeout. What does the switch lose by using time rather than something more direct, and what would "more direct" even be?

장비가 옮기거나 꺼져도 300초까지 옛 정보를 믿고, 조용히 살아 있는 장비는 지워 버린다. 더 직접적인 방법은 포트 연결이 끊긴 순간 그 포트의 항목을 바로 지우는 것이다.

# Task 2

Q. The first entry to come back, and why it had to be that one

게이트웨이 192.168.35.1이다. 바깥으로 가는 패킷은 전부 게이트웨이를 거치기 때문이다. 표는 13개에서 2개로 줄었는데, 사라진 11개는 모두 방송·멀티캐스트용 고정 항목이었고 나중에 저절로 돌아왔다.

Q. Why a server on the other side of the world is not in your ARP table

ARP는 같은 동네 안에서 IP를 MAC으로 바꾸는 것이고, 동네 밖으로 가는 패킷은 게이트웨이의 MAC으로 보내기 때문이다. 미국 서버(64.50.233.100, 191ms)에 접속한 뒤에도 표에 없었다.

Q. The two destination addresses from B2, and what each one means

요청은 ff:ff:ff:ff:ff:ff로 같은 동네 전부가 받고, 응답은 내 MAC 30:9c:23:9b:d3:8c로 나만 받는다. ARP는 처음 1분 4개(표를 비워서 생긴 2개 포함), 전체 160초 9개로 분당 약 3.4개였고, 장비 500대로 가정하면 분당 약 1,700개다.

# Task 3

Q. Your eviction rule, and the evidence you keep to run it

표에 있는 주소마다 최근에 찾아진 횟수를 세고, 표가 꽉 차면 횟수가 0인 주소를 뺀다. 표 밖의 주소는 기억하지 않는다. 낭비를 48% 줄였다.

Q. Whether you decline admissions, and what happened to the numbers when you tried

횟수가 0인 주소가 없으면 새 주소를 거절한다. 거절이 없으면 47.5%, 거절하면 47.6%로 효과는 거의 없었다.

Q. R6: the attack, in your own words, and one thing a switch could do about it

공격자가 가짜 출발 주소를 계속 보내면 표가 가짜로 차서 정상 주소가 밀려나고, 플러딩된 남의 프레임을 공격자도 보게 된다. 포트마다 배울 수 있는 주소 수를 제한하면 막을 수 있다. 내 방식은 가짜 주소가 1칸만 찼지만, 가짜 주소끼리 서로 보내면 41칸이 찼다.
