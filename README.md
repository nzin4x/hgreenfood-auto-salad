# 🍽️ hgreenfood-auto-salad

사내 식당 자동 예약 프로그램

선호 식단을 순서대로 예약하며, 결과를 data.json에 기록합니다.  
셀프 스케줄러로 한 번 실행하면 자동으로 매일 예약합니다.

## ⚠️ 주의 사항

- **개인정보 보호**: config.user.yaml 파일은 절대 공유하지 마세요
- **마스터 패스워드**: 분실 시 설정을 처음부터 다시 해야 합니다
- **Git 커밋 금지**: .gitignore에 포함되어 있으니 확인하세요

---

## 📋 사전 준비

1. **data.go.kr API 키 발급**
   - https://www.data.go.kr 회원가입
   - 공휴일 정보 API 키 발급 (무료)
   - https://www.data.go.kr/iim/api/selectApiKeyList.do

2. **사내 식당 앱 로그인 정보**
   - 사용자 ID
   - 비밀번호

---

## 🚀 설치 및 설정

### 1. 저장소 클론
```bash
git clone https://github.com/nzin4x/hgreenfood-auto-salad
cd hgreenfood-auto-salad
```

### 2. Python 가상환경 생성
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 초기 설정
```bash
python setup_config.py
```

다음 정보를 입력하게 됩니다:
1. 사용자 ID
2. 사용자 비밀번호 (입력 즉시 검증)
3. data.go.kr API 키 (입력 즉시 검증)
4. 선호 메뉴 순서 (예: `샌,샐,빵`)
5. 배달받을 층 (예: `5층`)
6. 마스터 패스워드 (민감 정보 암호화용, 8자 이상)

입력한 정보는 즉시 검증되며, 민감 정보는 암호화되어 저장됩니다.

---

## 💻 실행

```bash
python main.py
```

메뉴에서 원하는 작업을 선택할 수 있습니다:
1. 프로그램 시작 (자동 예약 실행)
2. 마스터 패스워드 변경
3. 환경 설정 재생성
4. 선호 식단 순서 변경
5. 예약 금지 날짜 관리 (휴가 등)
0. 종료

Enter키를 누르면 기본값(1번)이 선택됩니다.

---

## 🔧 동작 방식

### 자동 예약 흐름
```
프로그램 시작
  ↓
마스터 패스워드 입력 → 설정 파일 복호화
  ↓
로그인 (1회만)
  ↓
현재 시간 확인
  ↓
┌─────────────────────────┐
│ 이미 예약됨?           │ → Yes → 다음 근무일까지 대기
└─────────────────────────┘
  ↓ No
┌─────────────────────────┐
│ 휴일/주말?             │ → Yes → 다음 근무일까지 대기
└─────────────────────────┘
  ↓ No
┌─────────────────────────┐
│ 13시까지 대기          │
└─────────────────────────┘
  ↓
예약 시도 (5초 간격, 최대 10회)
  - 선호 메뉴 순서대로 시도
  - 하나라도 성공하면 종료
  ↓
다음 근무일까지 대기
```

### 예약 시도 규칙
- **시작 시간**: 13시 정각
- **재시도**: 5초 간격, 최대 10회
- **조기 종료 조건**:
  - 예약 성공
  - 이미 다른 메뉴 예약됨
  - 로그인 실패

### 메뉴 코드
- `샌`: 샌드위치 (0005)
- `샐`: 샐러드 (0006)
- `빵`: 베이커리 (0007)
- `헬`: 헬시세트 (0009)
- `닭`: 닭가슴살 (0010)

---

## 🧪 테스트

```bash
# 예약 테스트
python test_simple.py reserve

# 취소 테스트
python test_simple.py cancel

# 전체 테스트
python test_simple.py both
```

---

## 📁 파일 구조

```
hgreenfood-auto-salad/
├── app.py                  # 메인 프로그램
├── setup_config.py         # 설정 생성 프로그램
├── config.default.yaml     # 기본 설정 (수정 금지)
├── config.user.yaml        # 사용자 설정 (암호화됨, Git 제외)
├── holiday.py              # 휴일 관리
├── util.py                 # 유틸리티 함수
├── test_simple.py          # 테스트 도구
├── requirements.txt        # 의존성 목록
├── .gitignore              # Git 제외 파일 목록
├── data.json               # 예약 기록 (자동 생성)
├── app.log                 # 실행 로그 (자동 생성)
└── cookies.txt             # 로그인 세션 (자동 생성)
```

---

## 🔐 보안

### 암호화된 정보
- 사용자 비밀번호
- data.go.kr API 키

### 마스터 패스워드
- PBKDF2 알고리즘으로 키 생성
- Fernet 대칭 암호화 사용
- Salt는 설정 파일에 저장

### Git 보안
`.gitignore`에 포함된 파일:
- `config.user.yaml`
- `cookies.txt`
- `*.log`
- `data.json`

---

## 📝 설정 재생성

설정을 다시 하려면:
```bash
# 기존 설정 백업
mv config.user.yaml config.user.yaml.backup

# 새로운 설정 생성
python setup_config.py
```

---

## 🐛 문제 해결

### "마스터 패스워드가 올바르지 않습니다"
- 마스터 패스워드를 잊어버린 경우
- 해결: 설정 재생성

### "로그인 실패"
- ID/PW 확인
- 5회 연속 실패 시 계정 잠금 주의

### "API 키 검증 실패"
- data.go.kr 키 확인
- 키 활성화 여부 확인

---

## 📊 로그 확인

```bash
# 실시간 로그 확인
tail -f app.log

# 최근 100줄 확인
tail -n 100 app.log
```

---

## 🎯 TODO

- [x] 초기 설정 프로그램
- [x] 민감 정보 암호화
- [x] 예약 조회 기능
- [x] 예약 취소 기능
- [x] 무한 루프 버그 수정
- [x] 패킷 최소화
- [x] 휴일 캐싱
- [x] 로그인 세션 재사용
- [ ] 실행 파일 빌드 (Windows/Mac)
- [ ] 알림 기능 (선택사항) 

# TODO
- [x] 실행화일과 같은 위치에 있는 설정을 읽도록 상대경로 설정파일 코드 작성.
- [x] 스케쥴러 만들어서 매일 오후 1시에 자동으로 기동
- [x] 휴일 일정 연동
- [x] 휴일 캐싱
- [x] 신청 결과 기록
- [ ] 윈도우용 / 맥용 실행 프로그램 release 페이지에서 배포.

