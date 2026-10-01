# 3주차 · 관찰 기록 (Observations)

# Task 1

Q. Why did the root server not simply hand you the address?
root 서버는 전 세계의 모든 도메인 주소를 다 외우고 있는 게 아니라 어떤 TLD(.com, .kr 등)를
누가 담당하는지만 알고 있다. 그래서 바로 답을 주지 못하고 다음 서버를 알려줄 뿐이다.

Q. What did you do when a delegation arrived without glue, and how many extra lookups did that cost you?
네임서버의 이름만 알려주고 그 서버의 IP 주소(glue)는 안 주는 경우 네임서버의 이름 자체를 root부터 다시 찾아야 했다.
`www.stanford.edu`를 찾을 때 총 27번이나 서버에 물어봐야 했는데 glue를 제대로 받은 `www.korea.ac.kr`은 3번 만에 끝났다. glue가 없었던 것 때문에 추가로 약 24번을 더 물어보았다.

Q. How many servers did you end up asking for one name? Compare that with the single question your laptop normally asks its resolver.
이름 하나를 찾는 데 적게는 3개, 많게는 27개의 서버에 직접 물어봐야 했다.
우리 컴퓨터는 자기 리졸버(통신사 서버)에게 딱 한 번만 질문을 던지고 나머지 복잡한 과정은
전부 리졸버가 대신 처리해서 결과만 돌려준다. 


# Task 2

Q. The one-sentence difference between a delegation response and an answer response.
두 응답은 패킷의 형식 자체는 똑같고 안에 채워진 내용(위임이냐 진짜 답이냐)만 다르다는 걸 직접 확인할 수 있었다.

Q. Your third-party rule, the site it got wrong, and why.
규칙: 사이트 이름과 체인 끝 지점의 마지막 두 단어가 다르면 서드파티다. `www.wikipedia.org`
에서 틀렸는데 `wikimedia.org`로 끝나 서드파티로 판정됐지만 실제로는 위키미디어 재단이 소유한 자기 인프라였다.

Q. The steering number — and whether it supports claim (b) or not.
(b)를 뒷받침한다. CDN을 쓰는 11개 사이트 중 8개가 리졸버에 따라 다른 주소를 줬고 네트워크를 바꿔도 몇몇
사이트는 또 다른 주소를 줬다. 리졸버와 위치 둘 다 바뀌면 답도 바뀐다.

# Task 3

Q. The two things wrong with the baseline — a performance problem and a correctness problem, same root cause.
baseline은 실제 TTL을 무시하고 무조건 60초만 저장한다. TTL이 짧은 이름은 만료된 답을
계속 주고(정확성 문제) TTL이 긴 이름은 멀쩡한데도 금방 버려져 재조회한다(성능 문제). 이게 공통 원인이다.

Q. Your floor number, with the reasoning.
275회. 캐시가 유효할 때는 재조회 안 하고 만료됐을 때만 재조회하는 이상적인 캐시를 만들어
계산했더니 275회가 나왔다.

Q. Which record in the fixture the baseline handles worst, and why.
`www.microsoft.com`이 가장 심했다. TTL이 20초로 가장 짧으면서 가장 인기 있는 이름이기 때문이다.
