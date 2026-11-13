(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  let M, files = [], ALL_IDX = -1, sel = -1, shown = [];
  const state = { q: "", rp: new Set(), type: new Set(), topic: new Set(), sort: "title", view: "grid" };

  const fmtSize = b => b > 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB";
  const esc = s => s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ---- URL state: ?rp=RP3,RP4&type=...&topic=...&q=...&sort=...&view=list
  function readURL() {
    const p = new URLSearchParams(location.search);
    const names = { rp: M.rps, type: M.types, topic: M.topics };
    for (const k of ["rp", "type", "topic"])
      (p.get(k) || "").split(",").filter(Boolean).forEach(n => { const i = names[k].indexOf(n); if (i >= 0 && !(k === "rp" && n === "ALL")) state[k].add(i); });
    state.q = p.get("q") || ""; state.sort = p.get("sort") || "title"; state.view = p.get("view") || "grid";
  }
  function writeURL() {
    const p = new URLSearchParams();
    const names = { rp: M.rps, type: M.types, topic: M.topics };
    for (const k of ["rp", "type", "topic"]) if (state[k].size) p.set(k, [...state[k]].sort((a, b) => a - b).map(i => names[k][i]).join(","));
    if (state.q) p.set("q", state.q);
    if (state.sort !== "title") p.set("sort", state.sort);
    if (state.view !== "grid") p.set("view", state.view);
    const s = p.toString();
    history.replaceState(null, "", s ? "?" + s : location.pathname);
  }

  // ---- matching. Within a facet: OR. Across facets: AND. Docs tagged ALL always pass the RP facet.
  function pass(f, skip) {
    if (skip !== "rp" && state.rp.size && !(f.r.includes(ALL_IDX) || f.r.some(i => state.rp.has(i)))) return false;
    if (skip !== "type" && state.type.size && !f.k.some(i => state.type.has(i))) return false;
    if (skip !== "topic" && state.topic.size && !f.c.some(i => state.topic.has(i))) return false;
    if (state.q) {
      const hay = (f.t + " " + (f.i || "") + " " + f.p).toLowerCase();
      if (!state.q.toLowerCase().split(/\s+/).every(w => hay.includes(w))) return false;
    }
    return true;
  }

  function chips(el, key, names, field, isRP) {
    el.innerHTML = "";
    const mk = (label, count, on, zero, fn) => {
      const b = document.createElement("button");
      b.className = "chip" + (on ? " on" : "") + (zero ? " zero" : "");
      b.innerHTML = `${esc(label)} <small>${count}</small>`;
      b.onclick = fn; el.appendChild(b);
    };
    if (isRP) { // "ALL" chip = no reporting-period filtering; it is the default state
      const n = files.filter(f => pass(f, "rp")).length;
      mk("ALL", n, state.rp.size === 0, false, () => { state.rp.clear(); render(); });
    }
    names.forEach((n, i) => {
      if (isRP && i === ALL_IDX) return;
      const count = files.filter(f => pass(f, key) && (f[field].includes(i) || (isRP && f.r.includes(ALL_IDX)))).length;
      mk(n, count, state[key].has(i), !count && !state[key].has(i),
        () => { state[key].has(i) ? state[key].delete(i) : state[key].add(i); render(); });
    });
  }

  function cardHTML(f, n) {
    const thumb = f.m ? `<img loading="lazy" src="thumbs/${f.m}" alt="">` : esc(f.e.toUpperCase());
    const tags = f.r.map(i => `<span class="tag rp">${esc(M.rps[i])}</span>`).join("")
      + f.k.map(i => `<span class="tag type">${esc(M.types[i])}</span>`).join("")
      + f.c.map(i => `<span class="tag">${esc(M.topics[i])}</span>`).join("");
    const meta = [f.i, f.e.toUpperCase(), fmtSize(f.s)].filter(Boolean).join(" · ");
    return `<a class="card" role="listitem" data-n="${n}" href="${encodeURIComponent(f.p)}" target="_blank" rel="noopener">
      <div class="thumb">${thumb}</div>
      <div class="body"><div class="title">${esc(f.t)}</div><div class="meta">${esc(meta)}</div><div class="tags">${tags}</div></div></a>`;
  }

  function render() {
    const cmp = { title: (a, b) => a.t.localeCompare(b.t, undefined, { numeric: true }) || (a.i || "").localeCompare(b.i || ""),
      id: (a, b) => (a.i || "~" + a.t).localeCompare(b.i || "~" + b.t, undefined, { numeric: true }),
      size: (a, b) => b.s - a.s }[state.sort];
    shown = files.filter(f => pass(f)).sort(cmp);
    $("grid").className = "grid" + (state.view === "list" ? " list" : "");
    $("grid").innerHTML = shown.map(cardHTML).join("");
    $("status").textContent = `${shown.length} of ${files.length} documents` + (shown.length ? "" : " — no matches, try clearing a filter");
    chips($("f-rp"), "rp", M.rps, "r", true);
    chips($("f-type"), "type", M.types, "k");
    chips($("f-topic"), "topic", M.topics, "c");
    $("view").textContent = state.view === "list" ? "Cards" : "List";
    $("sort").value = state.sort;
    sel = -1; writeURL();
  }

  function move(d) {
    if (!shown.length) return;
    sel = Math.min(shown.length - 1, Math.max(0, sel + d));
    document.querySelectorAll(".card.sel").forEach(e => e.classList.remove("sel"));
    const c = document.querySelector(`.card[data-n="${sel}"]`);
    c.classList.add("sel"); c.scrollIntoView({ block: "nearest" });
  }

  function theme(t) { document.documentElement.dataset.theme = t; localStorage.setItem("theme", t); }

  fetch("manifest.json").then(r => r.json()).then(m => {
    M = m; files = m.files; ALL_IDX = m.rps.indexOf("ALL");
    $("site-title").textContent = m.title; document.title = m.title;
    $("count").textContent = `${m.count} documents · ${(m.bytes / 1048576).toFixed(0)} MB`;
    $("gen").textContent = "Updated " + m.generated.slice(0, 10);
    readURL(); $("q").value = state.q; render();
  }).catch(e => { $("status").textContent = "Could not load manifest.json: " + e; });

  $("q").oninput = e => { state.q = e.target.value.trim(); render(); };
  $("sort").onchange = e => { state.sort = e.target.value; render(); };
  $("view").onclick = () => { state.view = state.view === "list" ? "grid" : "list"; render(); };
  $("clear").onclick = () => { state.rp.clear(); state.type.clear(); state.topic.clear(); state.q = ""; $("q").value = ""; render(); };
  $("theme").onclick = () => theme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  theme(localStorage.getItem("theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));

  document.addEventListener("keydown", e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target === $("q")) { if (e.key === "Escape") e.target.blur(); return; }
    if (e.target.tagName === "SELECT") return;
    const k = e.key;
    if (k === "/") { e.preventDefault(); $("q").focus(); }
    else if (k === "j") move(1);
    else if (k === "k") move(-1);
    else if (k === "o" && sel >= 0) window.open(encodeURIComponent(shown[sel].p), "_blank");
    else if (k === "r" && shown.length) { sel = Math.floor(Math.random() * shown.length); move(0); }
    else if (k === "t") $("theme").click();
  });
})();
