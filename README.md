# hgreenfood-auto-salad
사내 샐러드 신청 자동화 프로그램
선호 식단을 순서대로 신청하며, 신청 결과를 data.json 에 표출한다.
셀프 스케쥴러이므로, 일단 실행해 두면 알아서 신청한다.

# 사용 방법

## config.user.yaml 파일 수정
- id, pw, 희망 식단 이니셜 목록을 저장
- data.go.kr 의 개인 API 키 발급
  - https://www.data.go.kr/iim/api/selectApiKeyList.do 에서 키 발급 및 확인
  - 일주일에 한번만 사용하므로 운영키를 발급 받을 필요 없음.
  - 임시공휴일 등 대응을 위한 매주 캐시 갱신 조회
- 설정파일과 app.py 또는 pyinstaller 로 만든 실행파일으 같은 위치에 저장하고 실행
  - 실행 프로그램으로 만들었을 경우, app.exe 위치에 config.user.yaml 과 config.default.yaml 을 같은 경로로 옮겨둔다.

## 실행
- 이 프로그램은 언제 실행하던 근무일 13시에 실행된다. 그 외시간에는 자동으로 sleep 이 걸림. (계속 틀어 놓으세요.)
- 실행이 성공하면 다음 근무일까지 자동 sleep
- 실행시 실패하면 정해진 duration 후에 다시 시도 (취소분 줍줍)

# TODO
- [x] 실행화일과 같은 위치에 있는 설정을 읽도록 상대경로 설정파일 코드 작성.
- [x] 스케쥴러 만들어서 매일 오후 1시에 자동으로 기동
- [x] 휴일 일정 연동
- [x] 휴일 캐싱
- [x] 신청 결과 기록 
