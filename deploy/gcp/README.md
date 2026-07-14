# Cross-Species Causal Atlas — GCP Cloud Run 배포

refimed와 동일 방식: **GitHub push → Cloud Build → Cloud Run**(서울). 한 컨테이너가
사이트 + 자연어 API(/ask)를 동일 출처로 서빙. OpenAI 키는 Secret Manager.

## 0. 사전 (1회)
```bash
gcloud config set project <YOUR_PROJECT_ID>
gcloud services enable cloudbuild.googleapis.com run.googleapis.com \
  secretmanager.googleapis.com containerregistry.googleapis.com

# OpenAI 키를 Secret Manager 에
printf '%s' "sk-..." | gcloud secrets create openai-api-key --data-file=-
# (갱신 시) printf '%s' "sk-..." | gcloud secrets versions add openai-api-key --data-file=-

# Cloud Build 서비스계정 권한 (시크릿 접근 + Cloud Run 배포)
PN=$(gcloud projects describe "$(gcloud config get-value project)" --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:${PN}@cloudbuild.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding "$(gcloud config get-value project)" \
  --member="serviceAccount:${PN}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
gcloud projects add-iam-policy-binding "$(gcloud config get-value project)" \
  --member="serviceAccount:${PN}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
# Cloud Run 런타임 서비스계정도 시크릿 접근 필요
CR=$(gcloud projects describe "$(gcloud config get-value project)" --format='value(projectNumber)')-compute@developer.gserviceaccount.com
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:${CR}" --role="roles/secretmanager.secretAccessor"
```

## A. 지금 바로 배포 (수동, 트리거 없이)
```bash
# 저장소 루트(causal-atlas)에서
gcloud builds submit --config cloudbuild.yaml .
# → Cloud Run URL 출력: https://causal-atlas-xxxx-du.a.run.app
```

## B. 자동 배포 (GitHub 트리거)
```bash
gcloud builds triggers create github \
  --repo-owner=brigs1 --repo-name=causal-atlas \
  --branch-pattern='^main$' --build-config=cloudbuild.yaml
# 이후 git push 하면 자동 빌드·배포
```

## 확인
```bash
URL=$(gcloud run services describe causal-atlas --region asia-northeast3 --format='value(status.url)')
curl -s "$URL/api/health"          # {"status":"ok","has_key":true}
open "$URL"                         # 사이트 + 🧠 자연어 질문 동작
```

## 참고
- 자연어 질문은 컨테이너 `/ask`(동일 출처)로 가므로 Cloudflare Worker·CORS 불필요.
- min-instances 0 → 무요청 시 비용 0 (콜드스타트 수 초). 상시 응답 원하면 min-instances 1.
- 사이트 정적 갱신 후 재배포: 다시 `gcloud builds submit --config cloudbuild.yaml .` (또는 git push).
