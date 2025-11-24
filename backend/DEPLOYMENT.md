# AWS Lambda & Cloudflare 배포 가이드

## 사전 준비

### 1. AWS CLI 설정
```bash
aws configure
# AWS Access Key ID, Secret Access Key, Region (ap-northeast-2) 입력
```

### 2. SAM CLI 설치 확인
Windows Git Bash 환경에서는 `sam.cmd`를 사용해야 합니다.
```bash
sam.cmd --version
```

### 3. S3 Bucket 생성 (배포 아티팩트용)
```bash
aws s3 mb s3://hgreenfood-lambda-deploy --region ap-northeast-2
```

`backend/samconfig.toml` 파일에서 s3_bucket을 업데이트:
```toml
s3_bucket = "hgreenfood-lambda-deploy"
```

### 4. SES 이메일 인증
**중요**: SES Sandbox 모드에서는 인증된 이메일만 발송 가능합니다.

```bash
# 발신자 이메일 인증
aws ses verify-email-identity --email-address no-reply@yourdomain.com --region ap-northeast-2

# 수신자 이메일 인증 (테스트용)
aws ses verify-email-identity --email-address your@email.com --region ap-northeast-2
```

이메일로 인증 링크가 발송되니 클릭하여 인증 완료하세요.

**프로덕션**: SES Sandbox 해제 신청 필요 (AWS Support → Service Limit Increase)

## 백엔드 배포 (AWS Lambda)

### 1. SSM Parameter Store에 Master Password 저장

비용 효율적인 SSM Parameter Store (SecureString)를 사용합니다.

```bash
aws ssm put-parameter \
    --name "/hgreenfood/master-password" \
    --value "your-secure-master-password-here" \
    --type "SecureString" \
    --region ap-northeast-2
```

### 2. SAM Build

```bash
cd backend
sam.cmd build
```

### 3. SAM Deploy

**중요**: 파라미터 값은 반드시 큰따옴표(`"`)로 감싸야 합니다. 특히 슬래시(`/`)나 공백이 포함된 값의 경우 필수입니다.

**권장 명령어** (확인 없이 자동 배포):
```bash
sam.cmd deploy --no-confirm-changeset --parameter-overrides MasterPasswordSsmParam="/hgreenfood/master-password" SesSenderEmail=nzin4x@gmail.com HolidayApiKey=c62c05fc5c76c77e6f0c65fb106636a9317f25d6f5cc6ecf64a3d93935c2485f DefaultTimezone="Asia/Seoul"
```

**첫 배포 또는 대화형 설정**:
```bash
sam.cmd deploy --guided
```

### 4. 배포 출력 확인

배포 완료 후 다음 정보가 출력됩니다:
- `ApiFunctionUrl`: API Gateway URL (프론트엔드 설정에 필요)
- `WorkerFunctionArn`: 워커 Lambda ARN
- `DynamoTableName`: DynamoDB 테이블 이름

## 프론트엔드 배포 (Cloudflare Pages)

1. **Cloudflare Dashboard** 접속 -> **Workers & Pages** -> **Create Application** -> **Pages** -> **Connect to Git**.
2. GitHub 리포지토리 연결.
3. 빌드 설정:
   - **Framework preset**: Vite
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
   - **Root directory**: `frontend`
4. **Environment variables**:
   - `VITE_API_BASE_URL`: 위에서 확인한 `ApiFunctionUrl` 값 입력.
5. **Save and Deploy**.

## DynamoDB 초기화

### 로컬 사용자 데이터를 AWS DynamoDB로 마이그레이션

```bash
# 로컬 DynamoDB에서 사용자 데이터 스캔
aws dynamodb scan \
  --table-name HGreenFoodAutoReserve \
  --endpoint-url http://localhost:8000 \
  --output json > local_users.json

# AWS DynamoDB에 사용자 데이터 등록 (각 사용자별로)
# 또는 register API 사용:
curl -X POST https://YOUR_API_URL/register \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "nzin4x",
    "password": "",
    "pin": "your-pin",
    "menuSeq": "샌,샐,빵",
    "floorNm": "5층",
    "email": "nzin4x@gmail.com"
  }'
```

## 테스트

### 1. API 테스트 (사용자 등록)
```bash
curl -X POST https://YOUR_API_URL/register \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "testuser",
    "password": "testpass123",
    "pin": "1234",
    "menuSeq": "샌,샐,빵",
    "floorNm": "5층",
    "email": "test@example.com"
  }'
```

### 2. 예약 확인 테스트
```bash
curl -X POST https://YOUR_API_URL/check-reservation \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "nzin4x",
    "targetDate": "2025-11-25"
  }'
```

### 3. 워커 Lambda 수동 실행 (테스트)
```bash
aws lambda invoke \
  --function-name hgreenfood-worker \
  --payload '{}' \
  --region ap-northeast-2 \
  response.json

cat response.json
```

## CloudWatch Logs 확인

```bash
# API Lambda 로그
aws logs tail /aws/lambda/hgreenfood-api --follow

# Worker Lambda 로그
aws logs tail /aws/lambda/hgreenfood-worker --follow
```

## EventBridge Rule 확인

워커 Lambda는 매일 평일 13:00 KST (04:00 UTC)에 자동 실행됩니다.

```bash
aws events describe-rule --name hgreenfood-worker-weekday
```

## 문제 해결

### SSM Parameter Store 권한 오류
Lambda 실행 역할에 SSM 읽기 권한이 필요합니다. SAM 템플릿에 이미 포함되어 있지만, 만약 권한 오류가 발생하면 다음 정책을 확인하세요:
```bash
aws iam attach-role-policy \
  --role-name hgreenfood-auto-salad-ApiFunctionRole-XXXXX \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess
```

### DynamoDB 권한 오류
SAM template에 이미 DynamoDBCrudPolicy가 포함되어 있으므로 자동으로 권한이 부여됩니다.

## 업데이트 배포

코드 수정 후:
```bash
cd backend
sam.cmd build
sam.cmd deploy
```

## 스택 삭제

```bash
sam.cmd delete
# 또는
aws cloudformation delete-stack --stack-name hgreenfood-auto-salad --region ap-northeast-2
```

⚠️ **주의**: DynamoDB 테이블도 함께 삭제되므로 사용자 데이터를 백업하세요!
