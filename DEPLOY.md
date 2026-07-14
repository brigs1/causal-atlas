# Cross-Species Causal Atlas — GitHub Pages 배포 가이드

정적 파일 2개만 올리면 되는 자체완결형 웹앱입니다. 서버 코드·빌드 불필요.

## 배포할 파일 (같은 폴더에)

| 파일 | 크기 | 역할 |
|---|---|---|
| `index.html` | 13 KB | 앱(검색·브리지·그래프 UI) |
| `kg.min.json.gz` | 1.05 MB | 데이터(22,320 검증 인과, gzip) |
| `.nojekyll` | 0 B | GitHub의 Jekyll 처리 건너뛰기(권장) |

> `index_standalone.html`(7 MB)은 **오프라인/이메일 첨부용**입니다. GitHub Pages엔 올릴
> 필요 없습니다(호스팅은 위 3개면 충분).

---

## 방법 1 — GitHub 웹 UI (CLI 없이, 가장 쉬움)

1. github.com 로그인 → **New repository** → 이름 예: `causal-atlas` → **Public** → Create.
2. 저장소 화면에서 **Add file ▸ Upload files**.
3. `index.html`, `kg.min.json.gz`, `.nojekyll` **3개를 드래그** → **Commit changes**.
   - (`.nojekyll`은 웹 UI에서 안 보일 수 있음 → 3-2 참고, 없어도 대개 동작)
4. **Settings ▸ Pages** → *Build and deployment* → Source: **Deploy from a branch** →
   Branch: **main** / **/ (root)** → **Save**.
5. 1~2분 뒤 상단에 뜨는 주소로 접속:
   `https://<사용자명>.github.io/causal-atlas/`

**3-2. `.nojekyll` 만들기(웹 UI):** Add file ▸ Create new file → 파일명에 `.nojekyll`
입력(내용 빈 채) → Commit. (또는 방법 2의 CLI 사용)

---

## 방법 2 — git CLI

```bash
cd factlog-kb/docs/web            # index.html, kg.min.json.gz, .nojekyll 있는 곳
git init && git branch -M main
git add index.html kg.min.json.gz .nojekyll
git commit -m "Cross-Species Causal Atlas"
git remote add origin https://github.com/<사용자명>/causal-atlas.git
git push -u origin main
```
그다음 **Settings ▸ Pages**에서 Branch **main / root** 선택 → Save.

---

## 왜 이 방식이 정적 호스팅에서 안전한가

- 데이터를 **미리 gzip한 `.gz` 파일**로 올리고, 브라우저에서 네이티브
  `DecompressionStream('gzip')`으로 해제합니다(외부 라이브러리 0).
- GitHub Pages는 `.gz`를 `Content-Type: application/gzip`으로, **`Content-Encoding` 없이**
  그대로 서빙합니다 → 우리 코드가 원본 gzip 바이트를 받아 직접 해제. 정상 동작.
- 전송량 **~1.07 MB**(index 13KB + gz 1.05MB). 첫 로드 후 검색은 전부 클라이언트측(빠름).

---

## 업데이트(데이터 갱신 시)

KG가 바뀌면 재빌드 후 두 파일만 다시 커밋:
```bash
# 1) 엣지 재추출(웹 폴더에서)
python - <<'PY'
# ... 프로젝트의 export 스크립트로 kg_edges.json 재생성 ...
PY
# 2) 컴팩트+gzip+호스팅 HTML 재빌드
python make_hosted.py            # → index.html, kg.min.json.gz 갱신
git add index.html kg.min.json.gz && git commit -m "update data" && git push
```

---

## 문제 해결

**Q. 화면이 "데이터 로딩 중…"에서 안 넘어감 / 콘솔에 gzip 오류**
드물게 CDN이 `.gz`에 `Content-Encoding: gzip`을 붙이면 브라우저가 이중 해제로 실패합니다.
그럴 땐 **압축 안 한 JSON**으로 전환(1줄 수정):
```bash
gunzip -k kg.min.json.gz         # → kg.min.json (5.2MB, GitHub Pages가 전송 시 자동 gzip)
```
`index.html`에서 로딩부를 교체:
```js
// 기존(.gz 수동 해제):
const r=await fetch('kg.min.json.gz');
const ds=new DecompressionStream('gzip');
const txt=await new Response(r.body.pipeThrough(ds)).text();const C=JSON.parse(txt);
// 대체(.json 직접):
const C=await (await fetch('kg.min.json')).json();
```
GitHub Pages는 텍스트 응답을 전송 계층에서 자동 gzip하므로 실제 전송량은 비슷(~1MB)합니다.

**Q. `file://`로 index.html을 더블클릭하면 안 열림**
정상입니다. 호스팅 버전은 `fetch`를 써서 HTTP가 필요합니다. **오프라인은
`index_standalone.html`**(데이터 내장)을 쓰세요.

**Q. 페이지가 404**
Settings ▸ Pages의 Branch/폴더 설정 확인, 커밋 후 1~2분 대기. 저장소가 **Public**인지 확인.

**Q. 커스텀 도메인**
Settings ▸ Pages ▸ Custom domain에 도메인 입력 + DNS에 CNAME(→ `<사용자명>.github.io`).
저장소 루트에 `CNAME` 파일(도메인 한 줄)도 커밋.

---

## 로컬에서 미리보기 (배포 전 확인)

```bash
cd factlog-kb/docs/web
python -m http.server 8000
# 브라우저에서 http://localhost:8000/  접속
```
