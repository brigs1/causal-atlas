# 자연어 질의 서버리스 함수 배포 (Cloudflare Worker)

웹앱의 "🧠 자연어로 질문하기" 기능을 켜는 백엔드입니다. **API 키를 브라우저에 노출하지
않고**, 검색·검색은 브라우저에서, **LLM 서술만** Worker가 담당합니다.

- 파일: `worker/worker.js` (서술 함수) · `worker/wrangler.toml` (설정)
- 왜 필요: GitHub Pages는 정적이라 서버 코드·비밀키를 둘 수 없음. Worker가 OpenAI 키를
  시크릿으로 보관하고 CORS로 브라우저 요청을 받음.

## 사전 준비
- **무료 Cloudflare 계정** (dash.cloudflare.com)
- **OpenAI API 키** (platform.openai.com)

---

## 방법 A — 대시보드 (CLI 없이)

1. Cloudflare 대시보드 ▸ **Workers & Pages** ▸ **Create** ▸ **Create Worker**.
2. 이름 `causal-atlas-ask` ▸ Deploy(기본 코드로 일단 배포).
3. **Edit code** ▸ `worker/worker.js` 내용 **전체 복사·붙여넣기** ▸ **Deploy**.
4. Worker ▸ **Settings ▸ Variables and Secrets** ▸ **Add** ▸
   - Type: **Secret**, Name: `OPENAI_API_KEY`, Value: (당신의 OpenAI 키) ▸ Save/Deploy.
5. Worker 주소 복사: `https://causal-atlas-ask.<계정>.workers.dev`

## 방법 B — wrangler CLI

```bash
cd worker
npx wrangler login                       # 브라우저로 Cloudflare 인증
npx wrangler secret put OPENAI_API_KEY   # 프롬프트에 OpenAI 키 붙여넣기
npx wrangler deploy                      # 배포 → workers.dev URL 출력
```

---

## 앱에 연결 (Worker URL 넣기)

`build_web.py`에서 한 줄 수정:
```js
const ASK_ENDPOINT="";   // → const ASK_ENDPOINT="https://causal-atlas-ask.<계정>.workers.dev";
```
그다음 재빌드 + 재배포:
```bash
python build_web.py && mv index.html index_standalone.html && python make_hosted.py
./deploy_ghpages.sh causal-atlas     # GitHub Pages 갱신
```
> 급하면 배포된 `index.html`의 `const ASK_ENDPOINT="";` 한 줄만 직접 고쳐 다시 올려도 됩니다
> (단, 다음 재빌드 때 다시 넣어야 함 → build_web.py 수정이 정석).

미설정 상태에선 질문 시 "답변 서버 미설정" 안내가 뜨고, **검색·브리지·그래프는 그대로 동작**합니다.

---

## 동작 확인

배포된 사이트에서 `선충 rab-7은 암을 어떻게 억제하나?` 질문 →
검증된 사실 기반 답변 + (PMID) 링크가 떠야 정상.

## 보안 · 비용 · 한도
- OpenAI 키는 **Worker 시크릿**에만 있고 브라우저·저장소에 노출 안 됨.
- Worker는 질문 + (클라이언트가 검색한) 검증 사실만 받고, 큰 데이터(수 MB)는 안 봄 → 경량.
- Cloudflare Workers 무료: 10만 요청/일. OpenAI는 사용량 과금(질문당 gpt-4o 소량).
- 남용 방지: 필요 시 worker.js에서 `Access-Control-Allow-Origin`을 당신 사이트 도메인으로
  제한하고, 간단한 rate-limit(예: Cloudflare Turnstile)을 추가하세요.

## 문제 해결
- **CORS 오류:** worker.js가 CORS 헤더를 반환합니다. 그래도 나면 브라우저 콘솔에서 프리플라이트(OPTIONS) 확인.
- **"server missing OPENAI_API_KEY secret":** 4단계의 시크릿을 안 넣었거나 이름 오타. `OPENAI_API_KEY`인지 확인.
- **openai 4xx:** OpenAI 키/크레딧 확인.
