# AWS 서버리스 마이그레이션 계획

## 1. 목표
- 단일 사용자용 로컬 Python 스크립트를 AWS 기반의 다중 사용자 서버리스 아키텍처로 이전한다.
- 마이그레이션 이후에도 로컬 실행 경로를 유지한다.

## 2. 아키텍처 개요
Serverless 접근 방식을 통해 비용과 운영 부담을 최소화한다.

### 2.1 컴퓨팅 (AWS Lambda)
- **Worker Lambda**: EventBridge(스케줄러)에 의해 트리거되어 예약 작업을 수행한다.
- **API Lambda**: 로그인, 설정 변경, 휴가 등록 등 사용자 요청을 처리한다.

### 2.2 데이터베이스 (Amazon DynamoDB, On-demand)
- 사용자 설정, 암호화된 자격 증명, 휴가 날짜 등을 저장한다.

### 2.3 트리거 (Amazon EventBridge Scheduler)
- 평일 13:00 KST마다 Worker Lambda를 트리거한다.

### 2.4 알림 (Amazon SES 또는 SNS)
- 예약 완료 알림과 로그인 인증 코드를 발송한다.

### 2.5 프론트엔드 (Cloudflare Pages)
- UI용 정적 웹 호스팅.

### 2.6 API 노출 (Lambda Function URLs)
- API Gateway 대비 비용 효율적인 대안으로 사용한다.

## 3. 주요 결정 사항

### 3.1 Lambda 구조: 단일 vs 다중 함수
- **권장**: 두 개의 논리적 Lambda로 분리 유지 (API / Worker).
- **이유**: 동기 사용자 요청과 비동기 예약 작업의 성격이 다르므로 진입점을 분리하는 것이 관리에 유리하다.
- **비용**: 호출 기반 과금이므로 함수 분리로 인한 추가 비용은 없다.

### 3.2 프로젝트 구조 (Monorepo)
VS Code 최상위 폴더에 프론트엔드와 백엔드를 포함한다.

```
hgreenfood-auto-salad/
├── backend/                # AWS SAM 기반 Serverless 프로젝트
│   ├── template.yaml       # AWS 리소스 정의 (Lambda, DynamoDB 등)
│   ├── src/
│   │   ├── app.py          # Lambda Handlers (API & Worker)
│   │   ├── core/           # 공통 로직 (로그인, 예약, Holiday) - 로컬과 공유
│   │   └── requirements.txt
│   └── events/             # 로컬 테스트용 이벤트
├── frontend/               # React (Vite) 프로젝트
│   ├── package.json
│   ├── src/
│   └── public/
├── local_script/           # 기존 로컬 실행용 스크립트 (backend/src/core 참조)
│   ├── main.py
│   └── config.user.yaml
└── README.md
```

### 3.3 이메일 발송 (Amazon SES)
- SES 프로덕션 액세스 권한 신청이 필요하다.
- **Sandbox 모드**: 검증된 이메일(본인 계정)로만 발송 가능.
- **Production 모드**: 모든 사용자에게 발송 가능.
- **전략**:
  - 개발 중에는 본인 이메일을 검증하여 테스트.
  - 배포 전 AWS 콘솔에서 Production Access 신청 (사용 목적: "사내 식당 예약 알림" 등).
  - 로그인 시 인증 코드 입력 행위를 수신 동의로 간주한다.

### 3.4 암호화 및 보안 (PIN 방식)
- **암호화**: Lambda 환경 변수 키로 현대그린푸드 비밀번호를 암호화하여 저장.
- **접근 제어**: 사용자는 4자리 PIN 번호를 설정하고, 설정 변경/예약 내역 조회 시 PIN으로 인증.
- **면책 조항 (UI)**:
  > 예약 처리를 위해 시스템(관리자)이 비밀번호를 복호화할 수 있는 구조입니다. 만약의 경우를 대비해 현대그린푸드 비밀번호를 다른 사이트와 다른, 유출되어도 무방한 것으로 변경하여 사용해주세요.

### 3.5 DynamoDB 테이블 설계 (Single Table Design)
- **테이블 이름**: `HGreenFoodAutoReserve`
- **Partition Key (PK)**: `PK` (String)
- **Sort Key (SK)**: `SK` (String)

#### 3.5.1 사용자 설정 (User Config)
- `PK = USER#{email}`
- `SK = CONFIG`
- 속성
  - `encrypted_password`: Lambda 환경 변수 키로 암호화된 현대그린푸드 비밀번호
  - `pin`: 4자리 접속 PIN
  - `api_key`: 공공데이터포털 키
  - `menu_seq`: 선호 메뉴 순서 리스트
  - `floor`: 배달 층 정보
  - `vacation_dates`: 휴가 날짜 목록(YYYYMMDD) 세트
  - `is_active`: 사용자 활성화 여부
  - `last_run_date`: 마지막 예약 시도 날짜 (중복 실행 방지)

#### 3.5.2 공휴일 정보 (Global Holidays)
- `PK = COMMON`
- `SK = HOLIDAY#{YYYYMM}` (예: `HOLIDAY#202511`)
- 속성
  - `dates`: 해당 월의 공휴일 목록(예: `['20251105', ...]`)

- **예약 내역**은 별도로 저장하지 않고, 필요 시 현대그린푸드 API를 통해 조회한다.

## 4. 예상 비용 (프리 티어 종료 후)
- **Lambda**: 월 40만 GB-초, 100만 요청까지 무료 (예상 사용량: 월 1만 GB-초 미만).
- **DynamoDB**: 25GB 스토리지, 월 2억 RCU/WCU 무료.
- **SES**: 월 62,000건 무료 (Lambda/EC2 호출 시).
- **EventBridge Scheduler**: 월 1,400만 건 무료.
- **Cloudflare Pages**: 항상 무료.
- **결론**: KMS를 사용하지 않는다면 계정 생성 1년 이후에도 유지 비용은 $0 수준이다 (KMS 사용 시 키당 $1/월 추가 비용 발생).
