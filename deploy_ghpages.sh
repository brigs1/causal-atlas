#!/usr/bin/env bash
# Cross-Species Causal Atlas — 통합 배포
#   (1) [--worker] Cloudflare Worker 배포 + OpenAI 시크릿 + ASK_ENDPOINT 자동 주입 + 재빌드
#   (2) GitHub Pages 사이트 배포 (사이트+README+가이드+worker+스크린샷, 비파괴)
#
# 사용법:
#   ./deploy_ghpages.sh [repo이름] [--worker] [--private]
#   예) ./deploy_ghpages.sh causal-atlas --worker
#
# 사전:
#   - gh 로그인(gh auth login)
#   - --worker 사용 시: npx 사용 가능 + 아래 환경변수
#       OPENAI_API_KEY        (필수; Worker 시크릿으로 등록)
#       CLOUDFLARE_API_TOKEN  (권장; 없으면 wrangler가 브라우저 로그인 시도)
set -euo pipefail

REPO="causal-atlas"; VIS="--public"; DO_WORKER=0
for a in "${@:-}"; do
  case "$a" in
    --worker) DO_WORKER=1;;
    --private) VIS="--private";;
    --*) ;;
    "") ;;
    *) REPO="$a";;
  esac
done
c(){ printf "\033[%sm%s\033[0m\n" "$1" "$2"; }
die(){ c "1;31" "✗ $1"; exit 1; }

command -v gh >/dev/null || die "gh(GitHub CLI) 필요"
gh auth status >/dev/null 2>&1 || die "gh 로그인 필요: gh auth login"
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
[[ -f index.html && -f kg.min.json.gz ]] || die "index.html / kg.min.json.gz 없음 (make_hosted.py 먼저)"
OWNER="$(gh api user --jq .login)"

# ─────────────────────────── (1) Worker 배포 ───────────────────────────
if [[ $DO_WORKER -eq 1 ]]; then
  c "1;36" "▶ [1/2] Cloudflare Worker 배포"
  command -v npx >/dev/null || die "npx 필요 (Node.js 설치)"
  [[ -n "${OPENAI_API_KEY:-}" ]] || die "환경변수 OPENAI_API_KEY 필요 (Worker 시크릿용)"
  [[ -f worker/worker.js ]] || die "worker/worker.js 없음"
  if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    c "1;33" "  경고: CLOUDFLARE_API_TOKEN 미설정 → wrangler가 브라우저 로그인 시도(대화형)."
    c "1;33" "        비대화형 원하면 CLOUDFLARE_API_TOKEN 발급해 export 후 재실행."
  fi
  ( cd worker
    c "0;37" "  wrangler deploy…"
    OUT="$(npx --yes wrangler@latest deploy 2>&1)" || { echo "$OUT"; die "wrangler deploy 실패"; }
    echo "$OUT" | grep -Eo "https://[a-z0-9.-]+workers\.dev" | head -1 > .worker_url || true
    c "0;37" "  OPENAI_API_KEY 시크릿 등록…"
    printf '%s' "$OPENAI_API_KEY" | npx --yes wrangler@latest secret put OPENAI_API_KEY >/dev/null \
      && c "0;32" "  시크릿 등록 완료" || c "1;33" "  시크릿 등록 실패(수동: wrangler secret put OPENAI_API_KEY)"
  )
  WURL="$(cat worker/.worker_url 2>/dev/null || true)"; rm -f worker/.worker_url
  [[ -n "$WURL" ]] || die "Worker URL 추출 실패 (배포 로그 확인)"
  c "1;32" "  Worker URL: $WURL"

  # ASK_ENDPOINT 주입 + 재빌드
  c "0;37" "  ASK_ENDPOINT 주입 + 재빌드…"
  sed -i "s#const ASK_ENDPOINT=\"[^\"]*\"#const ASK_ENDPOINT=\"$WURL\"#" build_web.py
  PY="$(command -v python3 || command -v python)"
  "$PY" build_web.py >/dev/null
  mv -f index.html index_standalone.html
  "$PY" make_hosted.py >/dev/null
  c "0;32" "  재빌드 완료 (ASK_ENDPOINT=$WURL)"
else
  c "0;37" "  (Worker 배포 생략 — 필요 시 --worker)"
fi

# ─────────────────────────── (2) 사이트 배포 ───────────────────────────
c "1;36" "▶ [2/2] GitHub Pages 배포: $OWNER/$REPO (${VIS#--})"
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
# 배포에 포함(비파괴): 사이트 + 문서 + worker + 스크린샷
cp index.html kg.min.json.gz "$STAGE/"; : > "$STAGE/.nojekyll"
for f in README.md DEPLOY.md WORKER_DEPLOY.md build_web.py make_hosted.py deploy_ghpages.sh; do [[ -f "$f" ]] && cp "$f" "$STAGE/"; done
mkdir -p "$STAGE/worker"; cp worker/worker.js worker/wrangler.toml "$STAGE/worker/" 2>/dev/null || true
if compgen -G "shot_bridge.png" >/dev/null || compgen -G "shot_graph.png" >/dev/null; then
  mkdir -p "$STAGE/screenshots"; [[ -f shot_bridge.png ]] && cp shot_bridge.png "$STAGE/screenshots/list.png"; [[ -f shot_graph.png ]] && cp shot_graph.png "$STAGE/screenshots/graph.png"
fi
cd "$STAGE"
git init -q; git checkout -q -b main 2>/dev/null || git branch -q -M main
git config user.name "$(gh api user --jq '.name // .login')"; git config user.email "${OWNER}@users.noreply.github.com"
git add -A
git commit -qm "Deploy Cross-Species Causal Atlas (site + worker + docs)"
if gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  git remote add origin "https://github.com/$OWNER/$REPO.git"; git push -qf -u origin main
else
  gh repo create "$REPO" $VIS --source=. --remote=origin --push
fi
# Pages 활성화
gh api "repos/$OWNER/$REPO/pages" >/dev/null 2>&1 || \
  gh api --method POST "repos/$OWNER/$REPO/pages" -f "source[branch]=main" -f "source[path]=/" >/dev/null 2>&1 || true

URL="$(gh api "repos/$OWNER/$REPO/pages" --jq .html_url 2>/dev/null || true)"; [[ -z "$URL" ]] && URL="https://$OWNER.github.io/$REPO/"
echo; c "1;32" "✔ 배포 완료 (Pages 빌드 1~2분)"
c "1;37" "  사이트: $URL"
[[ $DO_WORKER -eq 1 ]] && c "1;37" "  자연어 Q&A: 활성화됨 (Worker: ${WURL:-?})" || c "0;37" "  자연어 Q&A: 비활성(‘답변 서버 미설정’) — --worker로 켜기"
c "0;37" "  Repo: https://github.com/$OWNER/$REPO"
