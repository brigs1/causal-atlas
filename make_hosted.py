import json,gzip,re
from pathlib import Path
DB=json.load(open("kg_edges.json"))
REL=["positively_regulates","negatively_regulates","required_for","causes","regulates","produces","affects","contributes_to","develops_from"]
ri={r:i for i,r in enumerate(REL)}; DOM={"mito":0,"cancer":1}; UNS="unspecified/unspecified/unspecified"
edges=[[e["s"],ri.get(e["r"],0),e["o"],e["sp"],DOM[e["dom"]],e["pmid"],("" if(not e["ctx"] or e["ctx"]==UNS)else e["ctx"]),e["ev"]] for e in DB["edges"]]
compact={"species":DB["species"],"REL":REL,"edges":edges,"bridges":DB.get("bridges",{}),"chains":DB.get("chains",{})}
raw=json.dumps(compact,ensure_ascii=False,separators=(",",":")).encode("utf-8")
gz=gzip.compress(raw,9); Path("kg.min.json.gz").write_bytes(gz)
print(f"compact {len(raw)//1024}KB · gzip {len(gz)//1024}KB")

h=Path("index_standalone.html").read_text(encoding="utf-8")
h=re.sub(r'<script id="data"[^>]*>.*?</script>','',h,flags=re.S)
# 전역 함수 유지: 프리앰블만 let 선언으로
h=h.replace(
 "const DB=JSON.parse(document.getElementById('data').textContent);\nconst SPN=DB.species,BR=DB.bridges||{},CH=DB.chains||{};\ndocument.getElementById('tot').textContent=DB.edges.length.toLocaleString();",
 "let DB,SPN,BR,CH;")
# 말미 이벤트 바인딩 → boot()로 (데이터 로딩 후 실행)
old=("const qi=document.getElementById('q');qi.addEventListener('input',()=>render(qi.value));\n"
 "document.querySelectorAll('.ex b').forEach(b=>b.onclick=()=>go(b.textContent));\n"
 "document.querySelectorAll('#filters .chip').forEach(c=>c.onclick=()=>{c.classList.toggle('on');const sp=c.dataset.sp,dom=c.dataset.dom;if(sp)c.classList.contains('on')?spOn.add(sp):spOn.delete(sp);if(dom)c.classList.contains('on')?domOn.add(dom):domOn.delete(dom);render(qi.value);});")
new=("const qi=document.getElementById('q');\n"
 "async function boot(){\n"
 " try{const r=await fetch('kg.min.json.gz');const ds=new DecompressionStream('gzip');\n"
 " const txt=await new Response(r.body.pipeThrough(ds)).text();const C=JSON.parse(txt);const DOMN=['mito','cancer'];\n"
 " DB={species:C.species,bridges:C.bridges,chains:C.chains,edges:C.edges.map(a=>({s:a[0],r:C.REL[a[1]],o:a[2],sp:a[3],dom:DOMN[a[4]],pmid:a[5],ctx:a[6]||'',ev:a[7]}))};\n"
 " }catch(err){document.getElementById('results').innerHTML='<div class=none>데이터 로딩 실패: '+err+'</div>';return;}\n"
 " SPN=DB.species;BR=DB.bridges||{};CH=DB.chains||{};\n"
 " document.getElementById('tot').textContent=DB.edges.length.toLocaleString();\n"
 " document.getElementById('results').innerHTML='';\n"
 " qi.addEventListener('input',()=>render(qi.value));\n"
 " document.querySelectorAll('.ex b').forEach(b=>b.onclick=()=>go(b.textContent));\n"
 " document.querySelectorAll('#filters .chip').forEach(c=>c.onclick=()=>{c.classList.toggle('on');const sp=c.dataset.sp,dom=c.dataset.dom;if(sp)c.classList.contains('on')?spOn.add(sp):spOn.delete(sp);if(dom)c.classList.contains('on')?domOn.add(dom):domOn.delete(dom);render(qi.value);});\n"
 "}\nboot();")
assert old in h,"trailing block not found"
h=h.replace(old,new)
h=h.replace('<div id="results"></div>','<div id="results"><div class="none">데이터 로딩 중…</div></div>')
Path("index.html").write_text(h,encoding="utf-8")
print("호스팅 index.html:",Path("index.html").stat().st_size//1024,"KB · 전역함수 유지:",("function render(q)" in h and "async function boot" in h))
