# 5주차 · 관찰 기록

# Task 1

Q. What you return for /31 and /32, and why

보통은 맨 앞과 맨 뒤 주소를 빼고 쓰는데, 그러면 /31(주소 2개)과 /32(주소 1개)는 쓸 주소가 없어진다.
그래서 /31은 두 주소를 둘 다 쓰게 했고 /32는 그 주소 하나를 쓰게 했으며, 맨 뒤의 방송용 주소(브로드캐스트)는
빼지 않았으니 없음(None)으로 돌려준다.

Q. 10.20.30.70 matched four entries. List them, and say which rule picked the winner

`10.0.0.0/8`, `10.20.0.0/16`, `10.20.30.0/24`, `10.20.30.64/26` 네 개에 모두 들어간다.
이 중 가장 좁은 범위(/ 뒤 숫자가 가장 큰 것)를 고르는 규칙(longest prefix match)으로 /26인 lab-rack-2가 뽑혔다.

Q. If two entries had the same prefix length and different next hops, what did you do?

똑같은 주소 범위가 다른 목적지로 또 들어오면 어느 쪽이 맞는지 알 수 없어서, 덮어쓰지 않고 오류를 냈다.

# Task 2

Q. How many NATs you are behind, and the evidence

집 인터넷은 1겹이다. 공유기에게 바깥 주소를 물어보니 인터넷에서 보인 내 주소(211.187.75.22)와 같았다.
아이폰 핫스팟은 2겹으로 보인다. 아이폰이 한 번 바꾸고, 가만히 있었는데도 바깥 주소가 1분 만에 바뀌어서
통신사가 한 번 더 바꾸는 것 같다.

Q. What changed and what did not between your two networks, and why

집 인터넷에서 아이폰 핫스팟으로 바꾸니 집 안 주소(192.168.35.70 → 172.20.10.4)와 바깥 주소
(211.187.75.22 → 211.235.72.144)가 둘 다 바뀌었다. 주소를 나눠 주는 곳이 공유기에서 아이폰으로 바뀌었기
때문이다. 집 안에서만 쓰는 주소를 받는다는 점은 그대로였다.

Q. The Discover source address, and why it could not be anything else

0.0.0.0(주소 없음)이다. 주소를 받으러 가는 중이라 아직 내 주소가 없기 때문이다.
누구에게 물어야 할지도 몰라서 받는 쪽은 255.255.255.255(모두에게)로 보낸다.

# Task 3

Q. Which structure you chose, and what it cost in memory

프리픽스 길이별로 사전(dict)을 따로 만들어 묶는 방식을 골랐다(/24는 /24끼리, /16은 /16끼리).
메모리는 약 213KB로 원래 방식(354KB)보다 오히려 적었고, 1비트씩 따라가는 방식(트라이)은 약 4.5MB로 20배 넘게 들었다.

Q. R5: what your lookup time is now proportional to

경로 수가 아니라 표에 있는 프리픽스 길이의 종류 수(여기선 7가지, 최대 33가지)에 비례한다.

Q. Why the bit-walk is what hardware builds even when a hash table beats it in Python

파이썬에서는 사전 찾기가 한 번에 끝나지만 트라이는 1비트마다 반복을 한 번씩 돌아서 약 11배 느렸다.
하드웨어에서는 1비트 내려가기가 아주 단순한 일이라 여러 패킷을 줄지어 동시에 처리할 수 있고,
아무리 나빠도 32단계면 끝나서 걸리는 시간이 항상 일정하기 때문에 트라이를 쓴다.
