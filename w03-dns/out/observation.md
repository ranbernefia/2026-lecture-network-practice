# 3주차 · 관찰 기록

# Task 1

Q. Why did the root server not simply hand you the address?

root 서버는 전 세계의 모든 도메인 주소를 다 외우고 있는 게 아니라 어떤 TLD(.com, .kr 등)를
누가 담당하는지만 알고 있다. 그래서 바로 답을 주지 못하고 다음 서버를 알려줄 뿐이다.

Q. What did you do when a delegation arrived without glue, and how many extra lookups did that cost you?

네임서버의 이름만 알려주고 그 서버의 IP 주소(glue)는 안 주는 경우가 있었다. `www.stanford.edu`가
그랬는데, `.edu`가 `stanford.edu` 자신의 하위 도메인을 네임서버로 쓰면서도 glue를 안 줘서
그 네임서버 이름 자체를 root부터 다시 찾아야 했다. 그 결과 총 27번이나 서버에 물어봐야
했는데, glue를 제대로 받은 `www.korea.ac.kr`은 root→kr→korea.ac.kr 순서로 3번만 물어보고
끝났다. glue가 있었다면 stanford.edu도 root→edu→stanford.edu로 3번 만에 끝났을 것이므로,
27−3=24번이 glue가 없어서 더 물어본 것이다.

Q. How many servers did you end up asking for one name? Compare that with the single question your laptop normally asks its resolver.

이름 하나를 찾는 데 적게는 3개, 많게는 27개의 서버에 직접 물어봐야 했다. 평소에는
리졸버(통신사 서버일 수도 있고, 학교 서버나 8.8.8.8 같은 곳일 수도 있다)에게 딱 한 번만
질문을 던지면 나머지는 리졸버가 대신 처리한다. 게다가 리졸버는 한 번 찾은 답을 저장해두고
쓰기 때문에, 같은 이름을 다시 물을 때 매번 27번씩 다시 돌아다니지도 않는다.

# Task 2

Q. The one-sentence difference between a delegation response and an answer response.

위임 응답(143번)은 진짜 주소는 없고 "다음엔 `c.dns.kr`한테 물어봐"라는 안내만 들어있다.
답 응답(147번)은 진짜 주소(`163.152.6.10`)가 그대로 들어있다. 두 응답은 생김새(패킷
형식)는 완전히 똑같고, 안에 진짜 주소가 채워져 있는지 아닌지만 다르다.

Q. Your third-party rule, the site it got wrong, and why.

규칙: 사이트 이름 끝 두 단어와, CNAME을 따라간 끝 지점 이름의 끝 두 단어가 다르면 남의
서버(서드파티)라고 본다. `www.wikipedia.org`에서 이 규칙이 틀렸는데, `wikimedia.org`로
끝나서 남의 서버라고 판단했지만 사실 위키미디어 재단이 `wikipedia.org`와 `wikimedia.org`
둘 다 가진 자기 서버였다. `.ac.kr`, `.co.kr`처럼 끝 두 단어 자체가 흔하게 겹치는 경우엔,
서로 다른 기관인데도 같은 곳으로 착각할 수 있다는 약점도 있다.

Q. The steering number — and whether it supports claim (b) or not.

CDN을 쓰는 11개 사이트 중 8개가 묻는 리졸버(시스템/구글/Quad9)에 따라 다른 주소를 줬다.
집 와이파이에서 휴대폰 핫스팟으로 바꿔서 다시 물어봤을 때도, 몇몇 사이트(시스템 리졸버
기준 3개, 구글·Quad9 기준 각 2개)가 또 다른 주소를 줬다. 리졸버를 바꿔도, 내가 있는
곳을 바꿔도 답이 달라지니 "DNS가 가까운 곳으로 안내해준다"는 말은 맞는 것 같다.

# Task 3

Q. The two things wrong with the baseline — a performance problem and a correctness problem, same root cause.

baseline은 실제 TTL을 무시하고 무조건 60초만 저장한다. TTL이 짧은 이름은 만료된 답을
계속 주고(정확성 문제) TTL이 긴 이름은 멀쩡한데도 금방 버려져 재조회한다(성능 문제). 이게
공통 원인이다.

Q. Your floor number, with the reasoning.

275회. 정확성을 지키려면 처음 조회할 때와 TTL이 만료된 뒤 다시 그 이름을 찾을 때마다
최소 한 번은 다시 물어야 한다 — 그렇지 않으면 만료된 답을 주게 되므로 이보다 적게 조회할
방법은 없다. 캐시가 유효할 때는 재조회 안 하고 만료됐을 때만 재조회하는 이상적인 캐시를
만들어 계산했더니 정확히 275회가 나왔고, baseline의 325회보다 50회 적다.

Q. Which record in the fixture the baseline handles worst, and why.

`www.microsoft.com`이 가장 심했다. TTL이 20초로 60초보다 짧아서 매 주기 중 최대 40초
동안은 만료된 답을 줬고, 동시에 가장 인기 있는 이름이라 전체 stale 266건 중 189건(71%)이
여기서 나왔다.
