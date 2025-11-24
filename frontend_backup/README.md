# HGreenFood 자동 예약 서비스 - 프론트엔드

## 개요

이메일 인증 기반의 HGreenFood 자동 예약 서비스 웹 인터페이스입니다.

## 주요 기능

### 1. 이메일 인증
- 이메일 입력 시 6자리 인증 코드 발송 (AWS SES)
- 10분 유효기간
- 인증 코드 검증 후 계정 등록 또는 로그인

### 2. 디바이스 자동 로그인
- FingerprintJS를 사용한 디바이스 지문 생성
- 인증된 디바이스에서 자동 로그인
- 여러 디바이스 등록 가능

### 3. 사용자 설정
- 회사 사용자 ID/비밀번호
- 4자리 PIN
- 메뉴 우선순위 (예: 샌,샐,빵)
- 배달 층 정보

### 4. 예약 정보 대시보드
- 내일 예약 정보 실시간 조회
- 예약 상태 확인 (예약됨/대기중)
- 예약 완료 시 이메일 알림

## 설치 및 실행

### 1. API Gateway URL 설정

`index.html` 파일에서 API 엔드포인트 수정:

```javascript
const API_BASE_URL = 'https://xxx.execute-api.ap-northeast-2.amazonaws.com/Prod';
```

### 2. 로컬 테스트

```bash
# Python 간단한 HTTP 서버 실행
cd frontend
python -m http.server 8080

# 브라우저에서 접속
# http://localhost:8080
```

### 3. S3 정적 웹사이트 호스팅 (프로덕션)

```bash
# S3 버킷 생성
aws s3 mb s3://hgreenfood-frontend --region ap-northeast-2

# 정적 웹사이트 호스팅 설정
aws s3 website s3://hgreenfood-frontend \
  --index-document index.html \
  --error-document index.html

# 퍼블릭 액세스 허용
aws s3api put-bucket-policy \
  --bucket hgreenfood-frontend \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::hgreenfood-frontend/*"
    }]
  }'

# 파일 업로드
aws s3 cp index.html s3://hgreenfood-frontend/ --content-type "text/html"

# 접속 URL
# http://hgreenfood-frontend.s3-website.ap-northeast-2.amazonaws.com
```

### 4. CloudFront 배포 (선택 사항)

HTTPS 및 CDN을 위해 CloudFront 배포:

1. AWS 콘솔에서 CloudFront 배포 생성
2. Origin: S3 버킷 선택
3. Default Root Object: `index.html`
4. SSL Certificate: ACM 인증서 또는 CloudFront 기본 인증서
5. 배포 후 도메인 URL 확인

## 사용 흐름

### 첫 방문 (신규 사용자)

1. **이메일 입력**
   - 이메일 주소 입력
   - "인증 코드 받기" 클릭

2. **이메일 인증**
   - 이메일로 받은 6자리 코드 입력
   - "인증 확인" 클릭

3. **계정 설정**
   - 회사 사용자 ID, 비밀번호 입력
   - PIN, 메뉴 우선순위, 배달 층 입력
   - "등록 완료" 클릭

4. **대시보드**
   - 자동으로 대시보드 표시
   - 예약 정보 확인

### 재방문 (기존 사용자)

1. **자동 로그인**
   - 페이지 접속 시 디바이스 자동 인식
   - 등록된 디바이스면 자동 로그인
   - 바로 대시보드 표시

2. **신규 디바이스**
   - 이메일 인증 다시 진행
   - 기존 계정에 디바이스 추가 등록

## API 엔드포인트

### 이메일 인증

- **POST** `/auth/send-code`
  ```json
  {
    "email": "user@example.com"
  }
  ```

- **POST** `/auth/verify-code`
  ```json
  {
    "email": "user@example.com",
    "code": "123456",
    "deviceFingerprint": "abc123def456"
  }
  ```

### 디바이스 관리

- **POST** `/auth/check-device`
  ```json
  {
    "deviceFingerprint": "abc123def456"
  }
  ```

### 사용자 등록

- **POST** `/register`
  ```json
  {
    "userId": "nzin4x",
    "password": "password123",
    "pin": "1234",
    "menuSeq": "샌,샐,빵",
    "floorNm": "5층",
    "email": "user@example.com",
    "deviceFingerprint": "abc123def456"
  }
  ```

### 예약 조회

- **POST** `/check-reservation`
  ```json
  {
    "userId": "nzin4x",
    "targetDate": "2025-11-25"
  }
  ```

## 보안

### 디바이스 지문
- FingerprintJS를 사용한 브라우저/디바이스 고유 식별
- 세션 토큰 생성 시 이메일 + 디바이스 지문 조합

### 인증 코드
- 6자리 랜덤 숫자
- 10분 유효기간
- 일회용 (검증 후 자동 삭제)

### CORS
- API Gateway에서 CORS 허용 설정
- 프로덕션에서는 특정 도메인만 허용 권장

## 문제 해결

### 이메일이 안 옴
1. SES 이메일 인증 확인
2. SES Sandbox 모드 확인 (인증된 이메일만 수신 가능)
3. 스팸 폴더 확인

### 디바이스 자동 로그인 안 됨
1. 쿠키/로컬 스토리지 삭제 후 재시도
2. 시크릿 모드에서는 디바이스 지문이 다를 수 있음
3. 브라우저 업데이트 시 지문 변경 가능

### API 연결 오류
1. `API_BASE_URL` 설정 확인
2. API Gateway CORS 설정 확인
3. 브라우저 개발자 도구 → Network 탭에서 오류 확인

## 라이선스

MIT

## 문의

- GitHub Issues: https://github.com/nzin4x/hgreenfood-auto-salad/issues
