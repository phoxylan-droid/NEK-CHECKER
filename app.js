/* NEK CHECKER frontend — by @samvir1 */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

const state = {
  checkers: [],
  filter: "all",
  selected: null,
  running: false,
  abort: false,
  hits: [],
  stats: { checked: 0, total: 0, hits: 0, free: 0, bad: 0, err: 0, start: 0 },
};

async function api(path, opts) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts?.headers || {}) },
    ...opts,
  });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); }
  catch {
    throw new Error("API returned non-JSON (open via Vercel / local server, not file://)");
  }
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function showView(name) {
  $$(".view").forEach(v => v.classList.remove("active"));
  const el = $(`#view-${name}`);
  if (el) el.classList.add("active");
  $$(".nav-btn[data-view]").forEach(b => b.classList.toggle("active", b.dataset.view === name));
}

function log(msg, cls = "") {
  const pre = $("#log");
  const line = document.createElement("div");
  if (cls) line.className = cls;
  const ts = new Date().toLocaleTimeString();
  line.textContent = `[${ts}] ${msg}`;
  pre.appendChild(line);
  pre.scrollTop = pre.scrollHeight;
}

function updateProgress() {
  const s = state.stats;
  $("#p-checked").textContent = `${s.checked}/${s.total}`;
  $("#p-hits").textContent = s.hits;
  $("#p-free").textContent = s.free;
  $("#p-bad").textContent = s.bad;
  $("#p-err").textContent = s.err;
  const elapsed = Math.max(0.1, (Date.now() - s.start) / 1000);
  const cpm = Math.round(s.checked / elapsed * 60);
  $("#p-cpm").textContent = cpm;
  const pct = s.total ? Math.min(100, (s.checked / s.total) * 100) : 0;
  $("#bar-fill").style.width = pct + "%";
}

function renderCheckers() {
  const q = ($("#search")?.value || "").toLowerCase();
  const list = $("#checker-list");
  list.innerHTML = "";
  const items = state.checkers.filter(c => {
    if (state.filter !== "all" && c.cat !== state.filter) return false;
    if (q && !(`${c.name} ${c.id} ${c.cat}`.toLowerCase().includes(q))) return false;
    return true;
  });
  items.forEach(c => {
    const row = document.createElement("div");
    row.className = "checker-row" + (state.selected === c.id ? " selected" : "");
    row.innerHTML = `
      <div class="ico">${c.icon || "◆"}</div>
      <div class="meta"><b>${c.name}</b><span>${c.cat} · ${c.id}</span></div>
      <div class="go">RUN →</div>`;
    row.onclick = () => {
      state.selected = c.id;
      $("#sel-checker").value = c.id;
      $("#sel-hint").textContent = `${c.name} selected`;
      renderCheckers();
      showView("run");
    };
    list.appendChild(row);
  });
}

function fillSelect() {
  const sel = $("#sel-checker");
  sel.innerHTML = state.checkers.map(c =>
    `<option value="${c.id}">${c.icon || ""} ${c.name}</option>`
  ).join("");
}

function buildFilters() {
  const cats = ["all", ...new Set(state.checkers.map(c => c.cat))];
  const host = $("#filters");
  const strip = $("#cat-strip");
  host.innerHTML = "";
  strip.innerHTML = "";
  cats.forEach(cat => {
    const chip = document.createElement("button");
    chip.className = "chip" + (state.filter === cat ? " on" : "");
    chip.textContent = cat.toUpperCase();
    chip.onclick = () => { state.filter = cat; buildFilters(); renderCheckers(); };
    host.appendChild(chip);

    if (cat !== "all") {
      const c2 = chip.cloneNode(true);
      c2.onclick = () => { state.filter = cat; showView("checkers"); buildFilters(); renderCheckers(); };
      strip.appendChild(c2);
    }
  });
}

function parseLines(text) {
  return (text || "").split(/\r?\n/).map(l => l.trim()).filter(Boolean);
}

function firstProxy() {
  const lines = parseLines($("#proxies").value);
  return lines[0] || null;
}

async function runCheck() {
  if (state.running) return;
  const checker = $("#sel-checker").value;
  const combos = parseLines($("#combos").value);
  if (!checker) return log("Select a checker", "err");
  if (!combos.length) return log("Paste combos first", "err");

  state.running = true;
  state.abort = false;
  state.hits = [];
  state.stats = { checked: 0, total: combos.length, hits: 0, free: 0, bad: 0, err: 0, start: Date.now() };
  $("#btn-start").disabled = true;
  $("#btn-stop").disabled = false;
  $("#run-status").textContent = "running…";
  $("#log").innerHTML = "";
  updateProgress();
  log(`START ${checker} · ${combos.length} combos · proxy ${firstProxy() ? "yes" : "no"}`);

  // batch in small groups for serverless timeout safety
  const BATCH = 5;
  for (let i = 0; i < combos.length; i += BATCH) {
    if (state.abort) break;
    const slice = combos.slice(i, i + BATCH);
    try {
      const data = await api("/api/check", {
        method: "POST",
        body: JSON.stringify({
          checker,
          combos: slice,
          proxy: firstProxy(),
        }),
      });
      (data.results || []).forEach(r => {
        state.stats.checked += 1;
        const kind = (r.kind || "error").toLowerCase();
        if (kind === "hit") { state.stats.hits++; state.hits.push(r.line); log(r.line, "hit"); }
        else if (kind === "free") { state.stats.free++; log(r.line, "free"); }
        else if (kind === "bad") { state.stats.bad++; log(r.line, "bad"); }
        else { state.stats.err++; log(r.line, "err"); }
      });
    } catch (e) {
      slice.forEach(c => {
        state.stats.checked += 1;
        state.stats.err += 1;
        log(`${c} · ${e.message}`, "err");
      });
    }
    updateProgress();
  }

  state.running = false;
  $("#btn-start").disabled = false;
  $("#btn-stop").disabled = true;
  $("#run-status").textContent = state.abort ? "stopped" : "complete";
  log(`COMPLETE · hits ${state.stats.hits} · free ${state.stats.free} · bad ${state.stats.bad} · err ${state.stats.err}`);
}

function downloadHits() {
  if (!state.hits.length) return log("No hits yet", "err");
  const blob = new Blob([state.hits.join("\n") + "\n"], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `hits_${$("#sel-checker").value}_${Date.now()}.txt`;
  a.click();
}

function bindFiles() {
  $("#combo-file").onchange = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    $("#combos").value = await f.text();
  };
  $("#proxy-file").onchange = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    $("#proxies").value = await f.text();
  };
}

async function boot() {
  $$(".nav-btn[data-view]").forEach(b => b.onclick = () => showView(b.dataset.view));
  $$("[data-go]").forEach(b => b.onclick = () => showView(b.dataset.go));
  $("#btn-start").onclick = runCheck;
  $("#btn-stop").onclick = () => { state.abort = true; };
  $("#btn-dl").onclick = downloadHits;
  $("#search").oninput = renderCheckers;
  bindFiles();

  try {
    const health = await api("/api/health");
    if (health.ok) {
      $("#api-dot").classList.add("on");
      $("#api-dot").classList.remove("off");
    }
  } catch {
    $("#api-dot").textContent = "API offline";
  }

  try {
    const data = await api("/api/checkers");
    state.checkers = data.checkers || [];
    $("#stat-count").textContent = state.checkers.length;
    fillSelect();
    buildFilters();
    renderCheckers();
  } catch (e) {
    log("Failed to load checkers: " + e.message, "err");
    // fallback static list so UI still works
    state.checkers = [
      { id: "netflix", name: "Netflix", cat: "stream", icon: "🎬" },
      { id: "disney", name: "Disney+", cat: "stream", icon: "🏰" },
      { id: "crunchyroll", name: "Crunchyroll", cat: "stream", icon: "🍙" },
      { id: "nvidia", name: "NVIDIA / GFN", cat: "ai", icon: "🖥" },
      { id: "lovable", name: "Lovable.dev", cat: "ai", icon: "💜" },
      { id: "multi", name: "MULTI", cat: "multi", icon: "⚡" },
    ];
    $("#stat-count").textContent = state.checkers.length;
    fillSelect();
    buildFilters();
    renderCheckers();
  }
}

boot();
