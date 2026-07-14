/**
 * Cross-Species Causal Atlas — 서술 서버리스 함수 (Cloudflare Worker)
 *
 * 역할: 클라이언트가 이미 KG에서 "검증된 사실"을 검색해 보내면, 그 사실만으로
 *       자연어 답변을 서술(OpenAI). API 키는 Worker 시크릿(OPENAI_API_KEY)에 숨김.
 *       KG 데이터(수 MB)는 브라우저에 있으므로 Worker는 상태 없음·경량.
 *
 * factlog 철학: 제공된 검증 사실 밖 주장 금지 · 각 주장에 PMID 인용 · 없으면 "근거 없음".
 *
 * 배포: WORKER_DEPLOY.md 참고. 시크릿: wrangler secret put OPENAI_API_KEY
 */
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};
const j = (o, s = 200) =>
  new Response(JSON.stringify(o), { status: s, headers: { "Content-Type": "application/json", ...CORS } });

const NARR_SYS =
  "당신은 지식그래프의 검증된 사실만으로 답하는 신중한 생물학 서술자입니다. 제공된 사실 밖의 내용은 절대 지어내지 않습니다.";

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (req.method !== "POST") return j({ error: "POST only" }, 405);
    let body;
    try { body = await req.json(); } catch { return j({ error: "bad json" }, 400); }
    const question = (body.question || "").slice(0, 500);
    const facts = (body.facts || "").slice(0, 12000);
    const bridge = (body.bridge || "").slice(0, 2000);
    if (!question) return j({ error: "missing question" }, 400);
    if (!facts && !bridge) return j({ answer: "제공된 검증 근거로는 답할 수 없습니다 (해당 엔티티의 검증 인과가 KG에 없음)." });
    if (!env.OPENAI_API_KEY) return j({ error: "server missing OPENAI_API_KEY secret" }, 500);

    const prompt =
`아래는 지식그래프에서 3-렌즈로 검증된 인과 사실입니다(종·근거문·PMID 포함).
규칙(엄수): 아래 사실만 사용. 각 주장 끝에 (PMID xxxx). 제공 안 된 내용 금지. 질문이 사실로 안 덮이면 "제공된 검증 근거로는 답할 수 없습니다"라고 답. 외부 지식 추가 금지.

질문: ${question}

검증된 사실:
${facts}
${bridge}
JSON만 반환: {"answer":"위 사실만으로 쓴 2~5문장 한국어 답변, 각 주장에 (PMID) 인용"}`;

    let r;
    try {
      r = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${env.OPENAI_API_KEY}` },
        body: JSON.stringify({
          model: "gpt-4o", temperature: 0, response_format: { type: "json_object" },
          messages: [{ role: "system", content: NARR_SYS }, { role: "user", content: prompt }],
        }),
      });
    } catch (e) { return j({ error: "upstream fetch failed" }, 502); }
    if (!r.ok) return j({ error: "openai " + r.status }, 502);
    const data = await r.json();
    let ans = "";
    try { ans = JSON.parse(data.choices[0].message.content).answer; }
    catch { ans = data.choices?.[0]?.message?.content || "(서술 실패)"; }
    return j({ answer: ans });
  },
};
