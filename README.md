# hgreenfood-auto-salad
사내 샐러드 신청 자동화 프로그램
선호 식단을 순서대로 신청하며, 신청 결과를 data.json 에 표출한다.
셀프 스케쥴러이므로, 일단 실행해 두면 알아서 신청한다.

# 주의 사항
공유하면 공유할 수록, 내 확률을 줄어든다.

# 사용 방법

## 준비
- data.go.kr 회원 로그인 및 API 키 확보
- 샐러드 신청 앱 id/pw 확보

## 설치
- git clone https://github.com/nzin4x/hgreenfood-auto-salad
- python 설치 / venv 환경 준비
- pip install -r requirements.txt
- pip install pyinstaller
- pyinstaller --onefile app.py

## 기본 설정 구성 복사
- cp config.*.yaml dist/

## dist/config.user.yaml 파일 수정
- id, pw, 희망 식단 이니셜 목록을 저장
  - 예를 들어 샐,샌 을 적으면 샐러드 샌드위치 순으로 신청함.
- data.go.kr 의 개인 API 키 수정
  - https://www.data.go.kr/iim/api/selectApiKeyList.do 에서 키 발급 및 확인
  - 일주일에 한번만 사용하므로 운영키를 발급 받을 필요 없음.
  - 임시공휴일 등 대응을 위한 매주 캐시 갱신 조회

## 실행
- ./dist/app.exe 또는 ./dist/app
- 이 프로그램은 언제 실행하던 근무일 13시에 실행된다. 그 외시간에는 자동으로 sleep 이 걸림. (계속 틀어 놓으세요.)
- 실행이 성공하면 다음 근무일까지 자동 sleep
- 실행시 실패하면 정해진 duration 후에 다시 시도 

# TODO
- [x] 실행화일과 같은 위치에 있는 설정을 읽도록 상대경로 설정파일 코드 작성.
- [x] 스케쥴러 만들어서 매일 오후 1시에 자동으로 기동
- [x] 휴일 일정 연동
- [x] 휴일 캐싱
- [x] 신청 결과 기록
- [ ] 윈도우용 / 맥용 실행 프로그램 release 페이지에서 배포.

