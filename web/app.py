"""
Cross-Species Causal Atlas — Cloud Run 서비스 (FastAPI)

한 컨테이너가 (1) 정적 사이트(index.html, kg.min.json.gz)와
(2) 자연어 서술 API(/ask)를 **동일 출처로** 서빙 → Cloudflare Worker·CORS 불필요.
OpenAI 키는 환경변수(Cloud Run에선 Secret Manager: OPENAI_API_KEY)로만 주입.

factlog 철학: 클라이언트가 검색한 "검증된 사실"만으로 서술 + (PMID) 인용, 없으면 "근거 없음".

실행(로컬):  uvicorn web.app:app --host 0.0.0.0 --port 8080
"""
import json, os, urllib.request
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent   # index.html, kg.min.json.gz 가 있는 곳
app = FastAPI(title="Cross-Species Causal Atlas")

NARR_SYS = ("당신은 지식그래프의 검증된 사실만으로 답하는 신중한 생물학 서술자입니다. "
            "제공된 사실 밖의 내용은 절대 지어내지 않습니다.")

class AskIn(BaseModel):
    question: str = ""
    facts: str = ""
    bridge: str = ""

@app.get("/api/health")
def health():
    return {"status": "ok", "has_key": bool(os.environ.get("OPENAI_API_KEY"))}

@app.post("/ask")
def ask(body: AskIn):
    q = (body.question or "")[:500]
    facts = (body.facts or "")[:12000]
    bridge = (body.bridge or "")[:2000]
    if not q:
        return JSONResponse({"error": "missing question"}, status_code=400)
    if not facts and not bridge:
        return {"answer": "제공된 검증 근거로는 답할 수 없습니다 (해당 엔티티의 검증 인과가 KG에 없음)."}
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return JSONResponse({"error": "server missing OPENAI_API_KEY"}, status_code=500)
    prompt = (
        "아래는 지식그래프에서 3-렌즈로 검증된 인과 사실입니다(종·근거문·PMID 포함).\n"
        "규칙(엄수): 아래 사실만 사용. 각 주장 끝에 (PMID xxxx). 제공 안 된 내용 금지. "
        "질문이 사실로 안 덮이면 \"제공된 검증 근거로는 답할 수 없습니다\"라고 답. 외부 지식 추가 금지.\n\n"
        f"질문: {q}\n\n검증된 사실:\n{facts}\n{bridge}\n"
        "JSON만 반환: {\"answer\":\"위 사실만으로 쓴 2~5문장 한국어 답변, 각 주장에 (PMID) 인용\"}"
    )
    d = {"model": "gpt-4o", "temperature": 0, "response_format": {"type": "json_object"},
         "messages": [{"role": "system", "content": NARR_SYS}, {"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
        data=json.dumps(d).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=90).read())
        ans = json.loads(j["choices"][0]["message"]["content"]).get("answer", "")
    except Exception as e:
        return JSONResponse({"error": f"openai {type(e).__name__}"}, status_code=502)
    return {"answer": ans}

# 정적 사이트 (라우트 뒤에 마운트; index.html → /, kg.min.json.gz 등)
app.mount("/", StaticFiles(directory=str(ROOT), html=True), name="static")
