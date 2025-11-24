# Frontend Deployment Guide (Cloudflare Pages)

이 문서는 React 프론트엔드를 Cloudflare Pages에 배포하는 방법을 설명합니다. 이 프로젝트는 Monorepo 구조(backend/frontend 분리)이므로 **Root Directory** 설정이 중요합니다.

## 1. GitHub 저장소 준비

먼저 로컬의 변경사항(특히 `frontend` 폴더)을 GitHub 저장소에 Push 해야 합니다.

```bash
# 프로젝트 루트에서
git add frontend
git commit -m "Add frontend React application"
git push origin main
```

## 2. Cloudflare Pages 설정

1. **Cloudflare Dashboard** 접속
2. **Workers & Pages** > **Create Application** > **Pages** > **Connect to Git** 선택
3. GitHub 계정 연결 및 해당 리포지토리(`hgreenfood-auto-salad`) 선택
4. **Begin setup** 클릭

## 3. 빌드 설정 (Build Settings) **[중요]**

Monorepo 구조이므로 다음 설정을 정확히 입력해야 합니다.

| 설정 항목 | 값 | 설명 |
|---|---|---|
| **Project Name** | `hgreenfood-frontend` (원하는 이름) | |
| **Production branch** | `main` | |
| **Framework preset** | `Vite` | `React`가 아닌 `Vite`를 선택하세요. |
| **Build command** | `npm run build` | |
| **Build output directory** | `dist` | |
| **Root directory** | `frontend` | **필수**: 프론트엔드 코드가 있는 폴더 지정 |

## 4. 환경 변수 설정 (Environment Variables)

백엔드 API와 통신하기 위해 다음 환경 변수를 추가합니다.

| 변수명 | 값 | 설명 |
|---|---|---|
| `VITE_API_BASE_URL` | `https://1auqxaxnyd.execute-api.ap-northeast-2.amazonaws.com/Prod` | 배포된 API Gateway URL |

*참고: API Gateway URL은 `backend` 배포 후 `sam deploy` 출력에서 확인할 수 있습니다.*

## 5. 배포 완료 및 확인

**Save and Deploy**를 클릭하면 Cloudflare가 리포지토리를 복제하고, `frontend` 폴더로 이동하여(`Root directory`), `npm run build`를 실행하고, 결과물인 `dist` 폴더를 배포합니다.

배포가 완료되면 제공된 `*.pages.dev` URL로 접속하여 테스트하세요.
