#!/usr/bin/env python3
"""Generate tools/catalog_form.html: a self-contained checkbox grid for tagging documents.

Usage: python3 tools/make_catalog_form.py     (run from the repo root)
Open tools/catalog_form.html in a browser, tick boxes, click "Download answers",
then send the downloaded catalog_answers.json back (or run apply_catalog_answers.py on it).
"""
import csv, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import RPS, TYPES, TOPICS

split = lambda c: [x.strip() for x in (c or "").split(";") if x.strip()]
rows = []
with open("tools/catalog.csv", newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append({"file": r["file"], "rp": split(r["rp"]), "types": split(r["types"]), "topics": split(r["topics"])})
data = {"rows": rows, "facets": {"topics": TOPICS, "rp": RPS, "types": TYPES}}
html = TEMPLATE = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>CAR1459 tagging form</title>
<style>
:root{color-scheme:light}body{background:#fff;font:14px -apple-system,Segoe UI,sans-serif;margin:0;color:#1b2230}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ccd;padding:8px 14px;z-index:3;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
header button,header input{padding:6px 10px;font:inherit}
.tab.on{background:#2f5bd8;color:#fff}
table{border-collapse:separate;border-spacing:0;width:100%}
th{position:sticky;top:49px;background:#f0f3f9;border-bottom:1px solid #ccd;padding:6px 4px;font-size:12px;z-index:2;min-width:74px}
th.doc{text-align:left;min-width:380px;left:0;z-index:4}
td{border-bottom:1px solid #e6e9f0;padding:4px;text-align:center}
td.doc{text-align:left;position:sticky;left:0;background:#fff;z-index:1;max-width:520px}
tr:hover td,tr:hover td.doc{background:#f6f8ff}
td.doc small{display:block;color:#667}
td.doc a{color:#2f5bd8;text-decoration:none;font-weight:600}
input[type=checkbox]{width:18px;height:18px;cursor:pointer}
tr.done td.doc{border-left:4px solid #3a9d5d} tr.todo td.doc{border-left:4px solid #e0a030}
</style></head><body>
<header><b>Tag documents</b>
<button class="tab" data-f="topics">Topics</button><button class="tab" data-f="rp">Reporting period</button><button class="tab" data-f="types">Document type</button>
<input id="q" placeholder="Filter documents…"><label><input type="checkbox" id="todo"> only untagged in this tab</label>
<span id="prog"></span><button id="dl"><b>Download answers</b></button><span style="color:#667">Progress autosaves in this browser.</span></header>
<table><thead id="h"></thead><tbody id="b"></tbody></table>
<script>
const D=__DATA__, KEY="car1459-form-__HASH__", F=D.facets;
let tab="topics", st=JSON.parse(localStorage.getItem(KEY)||"null")||Object.fromEntries(D.rows.map(r=>[r.file,{rp:r.rp,types:r.types,topics:r.topics}]));
const $=id=>document.getElementById(id), save=()=>localStorage.setItem(KEY,JSON.stringify(st));
function draw(){
  const q=$("q").value.toLowerCase(), todo=$("todo").checked, cols=F[tab];
  $("h").innerHTML="<tr><th class='doc'>Document ("+D.rows.length+")</th>"+cols.map(c=>"<th>"+c+"</th>").join("")+"</tr>";
  $("b").innerHTML=D.rows.filter(r=>r.file.toLowerCase().includes(q)&&(!todo||!st[r.file][tab].length)).map(r=>{
    const v=st[r.file][tab], n=r.file.replace(/\.[^.]+$/,"");
    return "<tr class='"+(v.length?"done":"todo")+"'><td class='doc'><a href='../docs/"+encodeURIComponent(r.file)+"' target='_blank'>"+n+"</a><small>"+
      ["rp","types","topics"].filter(k=>k!==tab).map(k=>st[r.file][k].join(", ")||"–").join(" | ")+"</small></td>"+
      cols.map(c=>"<td><input type='checkbox' data-f='"+r.file.replace(/'/g,"&#39;")+"' data-v='"+c+"' "+(v.includes(c)?"checked":"")+"></td>").join("")+"</tr>"}).join("");
  document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("on",b.dataset.f===tab));
  const done=D.rows.filter(r=>st[r.file][tab].length).length; $("prog").textContent=done+"/"+D.rows.length+" tagged";
}
$("b").onchange=e=>{const t=e.target,a=st[t.dataset.f][tab],v=t.dataset.v;
  st[t.dataset.f][tab]=t.checked?[...a,v]:a.filter(x=>x!==v);save();
  const tr=t.closest("tr");tr.className=st[t.dataset.f][tab].length?"done":"todo";
  const done=D.rows.filter(r=>st[r.file][tab].length).length;$("prog").textContent=done+"/"+D.rows.length+" tagged"};
document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{tab=b.dataset.f;draw()});
$("q").oninput=draw;$("todo").onchange=draw;
$("dl").onclick=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(st,null,1)],{type:"application/json"}));a.download="catalog_answers.json";a.click()};
draw();
</script></body></html>'''.replace("__DATA__", json.dumps(data)).replace("__HASH__", hashlib.sha1(json.dumps(data).encode()).hexdigest()[:10])
Path("tools/catalog_form.html").write_text(html, encoding="utf-8")
print("wrote tools/catalog_form.html")
