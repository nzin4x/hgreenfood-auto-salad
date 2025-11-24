AWS 서버리스 마이그레이션 계획
목표
단일 사용자용 로컬 Python 스크립트를 AWS 기반의 다중 사용자 서버리스 아키텍처로 마이그레이션합니다. 동시에 로컬 실행 기능도 유지합니다.

아키텍처 개요
비용과 관리 부담을 최소화하기 위해 Serverless 접근 방식을 사용합니다.

컴퓨팅: AWS Lambda
Worker Lambda: EventBridge(스케줄러)에 의해 트리거되어 실제 예약 작업을 수행합니다.
API Lambda: 사용자 요청(로그인, 설정 변경, 휴가 등록 등)을 처리합니다.
데이터베이스: Amazon DynamoDB (On-demand 용량)
사용자 설정, 암호화된 자격 증명, 휴가 날짜 등을 저장합니다.
트리거: Amazon EventBridge Scheduler
평일 13:00 KST마다 Worker Lambda를 트리거합니다.
알림: Amazon SES (Simple Email Service) 또는 SNS
예약 완료 알림 및 로그인 인증 코드를 발송합니다.
프론트엔드: Cloudflare Pages
UI를 위한 정적 웹 호스팅을 제공합니다.
API 노출: Lambda Function URLs
API Gateway 대비 비용 효율적인 대안으로 사용합니다.
주요 결정 사항
1. Lambda 구조: 하나 vs 여러 개?
권장: 두 개의 논리적 함수로 분리 (유지).

이유: 20명/10초로 부하가 적더라도, **"사용자 요청(동기)"**과 **"예약 작업(비동기/스케줄)"**은 성격이 다릅니다. 코드는 공유하되 진입점(Handler)을 분리하는 것이 관리에 유리합니다.
비용: 호출 횟수 기반이므로 함수를 분리해도 비용 차이는 없습니다.
2. 프로젝트 구조 (Monorepo)
권장: VS Code 최상위 폴더 하나에 frontend와 backend를 둡니다.

hgreenfood-auto-salad/
├── backend/                # AWS SAM 프로젝트 (Serverless)
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
3. 이메일 발송 (SES)
중요: SES 프로덕션 액세스 권한 신청이 필요합니다.

Sandbox 모드 (기본): 검증된 이메일(내 이메일)로만 발송 가능합니다.
Production 모드: 아무에게나 발송 가능합니다.
전략:
개발 중에는 내 이메일만 검증하여 테스트.
배포 전 AWS 콘솔에서 "Production Access" 신청 (사용 목적: "사내 식당 예약 알림", "수신 동의한 사용자에게만 발송" 등으로 기재하면 보통 하루 내 승인).
사용자에게 별도 수신 동의 메일을 보낼 필요 없이, 로그인 시 인증 코드를 입력하는 행위 자체가 동의로 간주될 수 있습니다.
4. 암호화 및 보안 (PIN 방식)
변경: 서버 키 암호화 + PIN 인증 + 면책 조항.

암호화: 예약 작업을 위해 시스템이 복호화해야 하므로, Lambda 환경 변수 키로 현대그린푸드 비밀번호를 암호화하여 저장합니다.
접근 제어 (PIN): 사용자는 4자리 PIN 번호를 설정합니다. 설정 변경이나 예약 내역 조회 시 이 PIN으로 인증합니다. (마스터 패스워드 대체)
면책 조항 (UI 표시):
"예약 처리를 위해 시스템(관리자)이 비밀번호를 복호화할 수 있는 구조입니다. 만약의 경우를 대비해 현대그린푸드 비밀번호를 다른 사이트와 다른, 유출되어도 무방한 것으로 변경하여 사용해주세요."

5. DynamoDB 테이블 설계 (Single Table Design)
변경: 단일 테이블 전략 (One Table).

테이블 이름: HGreenFoodAutoReserve
Partition Key (PK): PK (String)
Sort Key (SK): SK (String)
엔티티 구조:

사용자 설정 (User Config)

PK: USER#{email}
SK: CONFIG
Attributes:
encrypted_password: String (현대그린푸드 비밀번호, Lambda Env Key로 암호화)
pin: String (4자리 접속 PIN)
api_key: String (공공데이터포털 키)
menu_seq: List (선호 메뉴 순서)
floor: String (배달 층)
vacation_dates
: Set (휴가 날짜 목록 YYYYMMDD)
is_active: Boolean
last_run_date: String (마지막 예약 시도 날짜 - 중복 실행 방지용)
공휴일 정보 (Global Holidays)

PK: COMMON
SK: HOLIDAY#{YYYYMM} (예: HOLIDAY#202511)
Attributes:
dates
: Set (해당 월의 공휴일 목록 ['20251105', ...])
장점: 테이블 관리가 단순해지고, PK 설계를 통해 데이터 분산 및 접근 패턴을 최적화할 수 있습니다.
예약 내역: 별도로 저장하지 않고, 필요 시 현대그린푸드 API를 직접 조회하여 보여줍니다.
예상 비용 (프리 티어 종료 후)
AWS의 프리 티어는 "12개월 무료"와 "항상 무료(Always Free)"로 나뉩니다. 본 프로젝트는 항상 무료 범위 내에 있어, 12개월이 지나도 비용은 $0에 가깝습니다.

Lambda: 항상 무료. 월 40만 GB-초, 100만 요청까지 무료. (현재 예상: 월 1만 GB-초 미만)
DynamoDB: 항상 무료. 25GB 스토리지, 월 2억 RCU/WCU 무료.
SES: 항상 무료. 월 62,000건 무료 (EC2/Lambda에서 호출 시).
EventBridge Scheduler: 월 1,400만 건 무료.
Cloudflare Pages: 항상 무료.
결론: 계정 생성 1년이 지나도 유지 비용은 $0입니다. (단, KMS 사용 시 키당 $1/월 발생하므로 환경 변수 방식 권장)

