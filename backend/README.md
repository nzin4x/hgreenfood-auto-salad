# Backend (AWS SAM)

H Green Food 자동 예약 백엔드는 DynamoDB에 저장된 설정만 사용하며 `config.user.yaml` 없이 동작합니다. 이 문서는 DynamoDB Local 기반 로컬 테스트와 AWS 배포 절차를 정리합니다.

## 준비물
- Python 3.11
- AWS SAM CLI ≥ 1.125.0
- Docker Desktop (sam local 컨테이너 실행용)
- AWS CLI
- DynamoDB Local (레포지토리의 `ext/dynamodb` 활용)

## 1. DynamoDB Local 실행
```bash
cd <repo-root>
java -Djava.library.path=ext/dynamodb/DynamoDBLocal_lib \
     -jar ext/dynamodb/DynamoDBLocal.jar \
     -sharedDb \
     -dbPath ext/dynamodb/data
```
- 기본 엔드포인트: `http://localhost:8000`
- SAM 컨테이너에서 접근 시 `http://host.docker.internal:8000` 사용

## 2. 테이블 및 사용자 프로필 생성
먼저 테이블을 생성합니다.
```bash
aws dynamodb create-table \
  --table-name HGreenFoodAutoReserve \
  --attribute-definitions AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S \
  --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --endpoint-url http://localhost:8000
```

사용자 정보는 `PK = USER#<userId>`, `SK = PROFILE` 구조로 저장합니다. API 핸들러가 사용자 등록/갱신을 담당하지만, 개발 초기에는 AWS CLI로 직접 입력할 수 있습니다.
```bash
aws dynamodb put-item \
  --table-name HGreenFoodAutoReserve \
  --item file://sample_user_item.json \
  --endpoint-url http://localhost:8000
```
`backend/sample_user_item.json` 파일에 자리표시자가 들어 있으니 실제 암호화 토큰(`userData_encrypted`, `_salt`, `data.go.kr.api.key_encrypted`)으로 바꿔서 사용하세요. 암호화 값은 기존 `setup_config.py` 실행 결과를 재활용할 수 있습니다.

## 3. SAM 빌드
```bash
cd backend
sam build
# Windows Docker 볼륨 마운팅 이슈로 인해 수동 복사 필요
cp -r src/* .aws-sam/build/ApiFunction/
cp -r src/* .aws-sam/build/WorkerFunction/
```

## 4. 로컬 테스트 (DynamoDB Local)
`env/local.json`은 DynamoDB Local을 가리키도록 아래와 같이 구성했습니다.
```json
{
  "ApiFunction": {
    "CONFIG_TABLE_NAME": "HGreenFoodAutoReserve",
    "DYNAMODB_ENDPOINT_URL": "http://host.docker.internal:8000",
    "MASTER_PASSWORD": "replace-with-master",
    "DEFAULT_USER_ID": "sample-user",
    "DEFAULT_TIMEZONE": "Asia/Seoul"
  },
  "WorkerFunction": {
    "CONFIG_TABLE_NAME": "HGreenFoodAutoReserve",
    "DYNAMODB_ENDPOINT_URL": "http://host.docker.internal:8000",
    "MASTER_PASSWORD": "replace-with-master",
    "DEFAULT_USER_ID": "sample-user",
    "DEFAULT_TIMEZONE": "Asia/Seoul"
  }
}
```
> Docker 컨테이너 밖에서 실행한다면 `DYNAMODB_ENDPOINT_URL`을 `http://localhost:8000`으로 변경하세요.

### API Lambda 호출
```bash
sam local invoke ApiFunction \
  --env-vars env/local.json \
  --event events/api_event.json
```

### 스케줄러 Lambda 호출
```bash
sam local invoke WorkerFunction \
  --env-vars env/local.json \
  --event events/worker_event.json
```

### 로컬 HTTP 엔드포인트
```bash
sam local start-api --env-vars env/local.json
# POST http://127.0.0.1:3000/ (body: events/api_event.json 형식)
```

## 3. 사용자 등록 Lambda 테스트

### 방법 1: Python 직접 실행 (권장, Rancher Desktop/WSL2 호환)
```bash
# 환경 변수 설정 후 테스트 스크립트 실행
python test_register_local.py
```

성공 시:
```json
{
  "message": "User registered successfully",
  "userId": "testuser1"
}
```

### 방법 2: sam local invoke (Docker 볼륨 이슈로 Rancher Desktop에서 불안정)
```bash
sam local invoke ApiFunction --env-vars env/local.json -e events/register_event.json
```
> **주의:** Rancher Desktop + WSL2 환경에서는 Docker 볼륨 마운팅 문제로 작동하지 않을 수 있습니다. Python 직접 실행 방법을 사용하세요.

### 등록 확인
DynamoDB에 사용자가 생성되었는지 확인:
```bash
aws dynamodb get-item \
  --table-name HGreenFoodAutoReserve \
  --key '{"PK":{"S":"USER#testuser1"},"SK":{"S":"PROFILE"}}' \
  --endpoint-url http://localhost:8000
```

## 5. AWS 배포
1. `samconfig.toml`의 S3 버킷/경로를 실제 값으로 수정
2. Secrets Manager에 마스터 패스워드를 저장하고 `MASTER_PASSWORD_SECRET_ARN` 환경 변수를 설정
3. `SES_SENDER_EMAIL`, `DEFAULT_TIMEZONE` 등 필요한 환경 변수를 지정
4. 배포 실행
```bash
sam deploy
```

EventBridge 스케줄러가 매일 13시 KST(UTC 04:00)에 워커 람다를 호출하며, 일요일에도 실행되어 다음 근무일(월요일) 예약을 시도합니다. 예약이 성공하면 SES로 알림 메일을 발송합니다.

## 6. 점검 체크리스트
- DynamoDB 테이블에 사용자 프로필이 존재하는가?
- Lambda IAM 역할이 DynamoDB/Secrets Manager/SES 권한을 갖는가?
- Worker Lambda 수동 호출 시 예약 로직과 이메일 발송이 정상 동작하는가?
