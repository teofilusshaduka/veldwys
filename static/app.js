/* VeldWys front-end. Offline-first: every read renders from cache immediately,
   then refreshes from the network; writes queue while offline and sync on reconnect. */

let userId = localStorage.getItem("veldwys_user_id");
let isSignup = false;
let map, obMap, marker, obMarker;
let state = { profile: null, animals: [], events: [], insights: [], herdFilter: "all",
              chats: [], chatId: null, docs: [], analytics: null };
let currentAudio = null;

const CHIP_KEYS = ["chip_overgrazed", "chip_stocking", "chip_move", "chip_lastyear",
                   "chip_bush", "chip_howlong", "chip_vacc", "chip_tenure"];
const SPECIES_ICON = { cattle: "🐄", goat: "🐐", sheep: "🐑", other: "🐾" };

/* ─────────────── cache + queue ─────────────── */
const cache = {
  get: (k, d = null) => { try { return JSON.parse(localStorage.getItem("vw_" + k)) ?? d; } catch { return d; } },
  set: (k, v) => { try { localStorage.setItem("vw_" + k, JSON.stringify(v)); } catch {} },
};
const queue = {
  all: () => cache.get("queue", []),
  add: (item) => { const q = queue.all(); q.push(item); cache.set("queue", q); },
  clear: () => cache.set("queue", []),
};

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error((await res.text()) || res.statusText);
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res;
}

/** POST that survives no-signal: queued locally and replayed on reconnect. */
async function post(path, body, queueable = true) {
  try {
    return await api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch (e) {
    if (queueable && !navigator.onLine) { queue.add({ path, body }); toast("📴 " + t("offline_banner")); return { queued: true }; }
    throw e;
  }
}

async function syncQueue() {
  const q = queue.all();
  if (!q.length) return;
  queue.clear();
  for (const item of q) {
    try { await api(item.path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(item.body) }); }
    catch { queue.add(item); }
  }
  toast("✅ " + t("saved"));
  refreshAll();
}

function setOnline(on) {
  document.body.classList.toggle("offline", !on);
  if (on) syncQueue();
}
window.addEventListener("online", () => setOnline(true));
window.addEventListener("offline", () => setOnline(false));

function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg; el.classList.add("show");
  clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove("show"), 2600);
}

/* ─────────────── auth ─────────────── */
function toggleAuthMode() {
  isSignup = !isSignup;
  document.getElementById("auth-btn").textContent = t(isSignup ? "signup" : "signin");
  document.getElementById("auth-toggle").textContent = t(isSignup ? "have_account" : "no_account");
  document.getElementById("auth-subtitle").textContent = t(isSignup ? "signup_sub" : "welcome_sub");
  document.getElementById("cap-list").style.display = isSignup ? "none" : "block";
  document.getElementById("auth-error").style.display = "none";
}

async function doAuth() {
  const u = document.getElementById("username").value.trim();
  const p = document.getElementById("password").value;
  if (!u || !p) return;
  const err = document.getElementById("auth-error");
  try {
    if (isSignup) await post("/api/signup", { username: u, password: p }, false);
    const data = await post("/api/login", { username: u, password: p }, false);
    userId = data.user_id;
    localStorage.setItem("veldwys_user_id", userId);
    document.body.classList.add("authed");
    if (isSignup) { buildLangGrid(); switchView("onboarding"); }
    else { await refreshAll(); switchView("dashboard"); }
  } catch (e) {
    let msg = String(e.message || e);
    try { msg = JSON.parse(msg).detail || msg; } catch {}
    err.textContent = msg; err.style.display = "block";
  }
}

function logout() {
  localStorage.removeItem("veldwys_user_id");
  userId = null; state = { profile: null, animals: [], events: [], insights: [], herdFilter: "all" };
  document.body.classList.remove("authed");
  document.getElementById("chat").innerHTML = "";
  document.getElementById("password").value = "";
  switchView("auth");
}

/* ─────────────── navigation ─────────────── */
function switchView(name) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById("view-" + name).classList.add("active");
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  document.getElementById("nav-" + name)?.classList.add("active");
  if (name === "settings") setTimeout(() => initMap("map"), 60);
  if (name === "onboarding") setTimeout(() => initMap("ob-map"), 60);
  if (name === "chat") { loadChats(); if (!document.getElementById("chat").children.length) renderChatGreeting(); }
  if (name === "dashboard") refreshDashboard();
  if (name === "herd") renderAnimals();
  if (name === "analytics") refreshAnalytics();
  if (name === "settings") loadDocs();
  if (name !== "chat") stopConversation();
}

/* ─────────────── language ─────────────── */
function buildLangGrid() {
  const grid = document.getElementById("ob-lang-grid");
  grid.innerHTML = Object.keys(I18N).map(code =>
    `<div class="lang-option ${code === LANG ? "selected" : ""}" data-lang="${code}" onclick="pickLang('${code}')">
       <span>${I18N[code]._native}</span><small>${I18N[code]._name}</small></div>`).join("");
}
function pickLang(code) {
  setLang(code);
  document.querySelectorAll(".lang-option").forEach(el => el.classList.toggle("selected", el.dataset.lang === code));
  updateLangBadge(); renderAll();
}
function updateLangBadge() { document.getElementById("lang-badge").textContent = LANG.toUpperCase(); }
function openLangPicker() {
  showModal(`<div class="modal-head"><h3>${t("choose_lang")}</h3><button class="modal-close" onclick="closeModal()">×</button></div>
    <div class="lang-grid">${Object.keys(I18N).map(c =>
      `<div class="lang-option ${c === LANG ? "selected" : ""}" onclick="pickLang('${c}');closeModal();saveLangPref('${c}')">
        <span>${I18N[c]._native}</span><small>${I18N[c]._name}</small></div>`).join("")}</div>`);
}
async function saveLangPref(code) {
  if (!userId || !state.profile) return;
  await post(`/api/profile?user_id=${userId}`, { ...profilePayload(), language: code });
  retranslateChat();
  refreshInsights();
  if (document.getElementById("view-analytics").classList.contains("active")) refreshAnalytics();
}

/* ─────────────── onboarding ─────────────── */
function obStep(n) {
  document.querySelectorAll(".ob-step").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".ob-dot").forEach(el => el.classList.remove("active"));
  document.getElementById("ob-step-" + n).classList.add("active");
  document.getElementById("dot-" + n).classList.add("active");
  if (n === 2) setTimeout(() => initMap("ob-map"), 60);
}

async function finishOnboarding(applyVacc) {
  const payload = {
    farm_name: document.getElementById("ob-farmname").value.trim(),
    language: LANG,
    lat: parseFloat(document.getElementById("ob-lat").value) || null,
    lon: parseFloat(document.getElementById("ob-lon").value) || null,
    camp_area_ha: parseFloat(document.getElementById("ob-area").value) || 0,
    cattle_count: parseInt(document.getElementById("ob-cattle").value) || 0,
    goat_count: parseInt(document.getElementById("ob-goats").value) || 0,
    sheep_count: parseInt(document.getElementById("ob-sheep").value) || 0,
  };
  await post(`/api/profile?user_id=${userId}`, payload);
  if (applyVacc) {
    const species = [];
    if (payload.cattle_count > 0) species.push("cattle");
    if (payload.goat_count > 0) species.push("goat");
    if (payload.sheep_count > 0) species.push("sheep");
    if (species.length) await post(`/api/protocols/apply?user_id=${userId}`, { species });
  }
  await refreshAll();
  obStep(5);
}

/* ─────────────── map ─────────────── */
function initMap(elId) {
  const isOb = elId === "ob-map";
  let m = isOb ? obMap : map;
  const latEl = document.getElementById(isOb ? "ob-lat" : "p-lat");
  const lonEl = document.getElementById(isOb ? "ob-lon" : "p-lon");
  const lat = parseFloat(latEl.value), lon = parseFloat(lonEl.value);

  if (!m) {
    m = L.map(elId, { attributionControl: false }).setView([lat || -22.56, lon || 17.06], lat ? 11 : 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 17 }).addTo(m);
    m.on("click", (e) => {
      const mk = isOb ? obMarker : marker;
      if (mk) m.removeLayer(mk);
      const nm = L.marker(e.latlng).addTo(m);
      if (isOb) obMarker = nm; else marker = nm;
      latEl.value = e.latlng.lat.toFixed(5); lonEl.value = e.latlng.lng.toFixed(5);
      showRegion(isOb, e.latlng.lat, e.latlng.lng);
    });
    if (isOb) obMap = m; else map = m;
    if (lat && lon) { const nm = L.marker([lat, lon]).addTo(m); if (isOb) obMarker = nm; else marker = nm; }
  } else {
    setTimeout(() => m.invalidateSize(), 80);
    if (lat && lon) {
      m.setView([lat, lon], 11);
      const mk = isOb ? obMarker : marker;
      if (mk) mk.setLatLng([lat, lon]);
      else { const nm = L.marker([lat, lon]).addTo(m); if (isOb) obMarker = nm; else marker = nm; }
    }
  }
  if (lat && lon) showRegion(isOb, lat, lon);
}

// Mirror of the backend's nearest-centroid region lookup, so the pin labels instantly offline.
const REGIONS = { "Zambezi": [-17.8, 24.3], "Kavango East": [-18.2, 20.8], "Kavango West": [-18.0, 19.3],
  "Kunene": [-19.5, 13.8], "Omusati": [-18.0, 14.9], "Oshana": [-18.0, 15.7], "Ohangwena": [-17.6, 16.3],
  "Oshikoto": [-18.4, 16.9], "Otjozondjupa": [-20.5, 17.5], "Omaheke": [-21.8, 19.7], "Erongo": [-21.8, 15.1],
  "Khomas": [-22.6, 17.1], "Hardap": [-24.5, 17.5], "Karas": [-27.0, 17.8] };
function regionOf(lat, lon) {
  let best = "Khomas", bd = Infinity;
  for (const [r, [a, b]] of Object.entries(REGIONS)) {
    const d = (lat - a) ** 2 + (lon - b) ** 2;
    if (d < bd) { bd = d; best = r; }
  }
  return best;
}
function showRegion(isOb, lat, lon) {
  const el = document.getElementById(isOb ? "ob-region" : "p-region");
  if (!el) return;
  el.style.display = "inline-flex";
  el.querySelector("span").textContent = `${t("region_detected")}: ${regionOf(lat, lon)}`;
}

/* ─────────────── data loading ─────────────── */
async function refreshAll() {
  if (!userId) return;
  renderFromCache();
  try {
    const [profile, animals, events] = await Promise.all([
      api(`/api/profile?user_id=${userId}`),
      api(`/api/animals?user_id=${userId}`),
      api(`/api/events?user_id=${userId}&upcoming=true&days=60`),
    ]);
    state.profile = profile; state.animals = animals; state.events = events;
    cache.set("profile", profile); cache.set("animals", animals); cache.set("events", events);
    if (profile.language && profile.language !== LANG) setLang(profile.language);
    setOnline(true);
  } catch { setOnline(false); }
  renderAll();
  refreshInsights();
}

function renderFromCache() {
  state.profile = cache.get("profile", state.profile);
  state.animals = cache.get("animals", []);
  state.events = cache.get("events", []);
  state.insights = cache.get("insights", []);
  renderAll();
}

async function refreshInsights() {
  try {
    state.insights = await api(`/api/insights?user_id=${userId}`);
    cache.set("insights", state.insights);
  } catch {}
  renderInsights();
}

function refreshDashboard() { renderInsights(); renderStats(); renderUpcoming(); }

function renderAll() {
  applyI18n(); updateLangBadge(); buildChips(); renderProfileForm();
  renderStats(); renderInsights(); renderUpcoming(); renderAnimals(); renderHerdFilters();
  document.getElementById("farm-label").textContent =
    state.profile ? (state.profile.farm_name || state.profile.region || "") : "";
}

/* ─────────────── dashboard render ─────────────── */
function renderStats() {
  const p = state.profile; if (!p) return;
  const herd = p.herd || { total_animals: 0, total_lsu: 0 };
  document.getElementById("s-animals").textContent = herd.total_animals || 0;
  document.getElementById("s-lsu").textContent = herd.total_lsu || 0;
  document.getElementById("s-land").textContent = p.camp_area_ha || 0;
  document.getElementById("s-region").textContent = p.region || "—";
}

function renderInsights() {
  const el = document.getElementById("insights-list");
  if (!state.insights.length) { el.innerHTML = `<div class="empty">…</div>`; return; }
  el.innerHTML = state.insights.map((i, idx) => {
    const [title, detail, question] = insightText(i);
    return `
    <div class="insight ${i.severity}" onclick="askFromInsight(${idx})">
      <div class="insight-icon">${i.icon}</div>
      <div style="flex:1;min-width:0;">
        <div class="insight-title">${esc(title)}</div>
        <div class="insight-detail">${esc(detail)}</div>
        ${question ? `<div class="insight-cta">💬 ${esc(question)}</div>` : ""}
      </div>
    </div>`; }).join("");
}

/** Insights arrive as a key + vars so they can be shown in the farmer's language. */
function insightText(i) {
  if (i.key && I18N[LANG]?.[`ins_${i.key}_t`]) {
    return [tf(`ins_${i.key}_t`, i.vars), tf(`ins_${i.key}_d`, i.vars), tf(`ins_${i.key}_q`, i.vars)];
  }
  return [i.title, i.detail, i.question];   // fallback to the English the backend sent
}

function askFromInsight(idx) {
  const q = insightText(state.insights[idx] || {})[2];
  if (!q) return;
  switchView("chat");
  document.getElementById("chat-input").value = q;
  sendChat();
}

/** Built-in protocol reminders carry a tkey so they show in the farmer's language.
 *  Anything the farmer typed themselves is shown exactly as they wrote it. */
function eventText(e) {
  if (e.tkey && I18N[LANG]?.[e.tkey]) {
    return { title: t(e.tkey), detail: t(e.tkey + "_d") };
  }
  return { title: e.description || e.event_type, detail: "" };
}

function renderUpcoming() {
  const el = document.getElementById("upcoming-list");
  const soon = (state.events || []).slice(0, 6);
  if (!soon.length) { el.innerHTML = `<div class="empty">${t("no_upcoming")}</div>`; return; }
  el.innerHTML = soon.map(e => {
    const { title, detail } = eventText(e);
    return `
    <div class="event-row ${e.overdue ? "overdue" : ""}">
      <div class="event-main">
        <div class="event-desc">${esc(title)}</div>
        ${detail ? `<div class="event-sub">${esc(detail)}</div>` : ""}
        <div class="event-meta ${e.overdue ? "red" : ""}">${e.overdue ? "⚠️ " : "📅 "}${e.due_date}${e.animal_tag ? " · " + esc(e.animal_tag) : ""}</div>
      </div>
      <button class="chk-btn" onclick="completeEvent(${e.id})" title="${t("mark_done")}">✓</button>
    </div>`; }).join("");
}

async function completeEvent(id) {
  await post(`/api/events/${id}/complete?user_id=${userId}`, {});
  state.events = state.events.filter(e => e.id !== id);
  cache.set("events", state.events);
  renderUpcoming(); refreshInsights();
  toast("✅ " + t("mark_done"));
}

/* ─────────────── morning briefing ─────────────── */
async function playBriefing() {
  const box = document.getElementById("brief-text");
  box.style.display = "block"; box.textContent = t("brief_loading");
  try {
    const data = await api(`/api/briefing?user_id=${userId}&lang=${LANG}`);
    box.textContent = data.text;
    speak(data.text);
  } catch { box.textContent = t("offline_chat"); }
}

/* ─────────────── herd ─────────────── */
function renderHerdFilters() {
  const el = document.getElementById("herd-filters");
  const count = (sp) => (state.animals || []).filter(a => sp === "all" || a.species === sp).length;
  const opts = [["all", `🐾 ${t("stat_animals")}`], ["cattle", `${SPECIES_ICON.cattle} ${t("cattle")}`],
                ["goat", `${SPECIES_ICON.goat} ${t("goats")}`], ["sheep", `${SPECIES_ICON.sheep} ${t("sheep")}`]];
  el.innerHTML = opts.map(([k, label]) =>
    `<div class="filter-chip ${state.herdFilter === k ? "on" : ""}" onclick="state.herdFilter='${k}';renderHerdFilters();renderAnimals();">${label} <b>${count(k)}</b></div>`).join("");
}

function renderAnimals() {
  const el = document.getElementById("animal-list");
  const q = (document.getElementById("herd-search")?.value || "").toLowerCase();
  let list = state.animals || [];
  if (state.herdFilter !== "all") list = list.filter(a => a.species === state.herdFilter);
  if (q) list = list.filter(a => `${a.tag} ${a.name} ${a.breed} ${a.notes}`.toLowerCase().includes(q));
  if (!list.length) { el.innerHTML = `<div class="empty">${t("herd_empty")}</div>`; return; }
  el.innerHTML = list.map(a => `
    <div class="animal-card" onclick="openAnimalDetail(${a.id})">
      ${a.photo_path ? `<img class="animal-photo" src="${esc(a.photo_path)}">`
                     : `<div class="animal-photo">${SPECIES_ICON[a.species] || "🐾"}</div>`}
      <div class="animal-info">
        <div class="animal-tag">${esc(a.tag || a.name || "#" + a.id)}</div>
        <div class="animal-meta">${esc([a.name && a.tag ? a.name : "", a.breed, a.sex ? t(a.sex) : "", a.dob].filter(Boolean).join(" · ")) || t(a.species)}</div>
      </div>
      <span class="pill ${a.status}">${t(a.status)}</span>
    </div>`).join("");
}

/* ─────────────── modals ─────────────── */
function showModal(html) {
  document.getElementById("modal-content").innerHTML = html;
  document.getElementById("modal").classList.add("open");
}
function closeModal() { document.getElementById("modal").classList.remove("open"); }
document.getElementById("modal").addEventListener("click", e => { if (e.target.id === "modal") closeModal(); });

function openAnimalModal(a = null) {
  const v = a || {};
  showModal(`
    <div class="modal-head"><h3>${a ? esc(a.tag || a.name || t("add_animal")) : t("add_animal")}</h3>
      <button class="modal-close" onclick="closeModal()">×</button></div>
    <div class="row-2">
      <div><label class="field">${t("tag")}</label><input id="a-tag" value="${esc(v.tag || "")}"></div>
      <div><label class="field">${t("name")}</label><input id="a-name" value="${esc(v.name || "")}"></div>
    </div>
    <div class="row-2">
      <div><label class="field">${t("species")}</label><select id="a-species">
        ${["cattle", "goat", "sheep", "other"].map(s => `<option value="${s}" ${v.species === s ? "selected" : ""}>${SPECIES_ICON[s]} ${t(s === "cattle" ? "cattle" : s === "goat" ? "goats" : s === "sheep" ? "sheep" : "species")}</option>`).join("")}
      </select></div>
      <div><label class="field">${t("sex")}</label><select id="a-sex">
        <option value=""></option><option value="female" ${v.sex === "female" ? "selected" : ""}>${t("female")}</option>
        <option value="male" ${v.sex === "male" ? "selected" : ""}>${t("male")}</option></select></div>
    </div>
    <div class="row-2">
      <div><label class="field">${t("breed")}</label><input id="a-breed" value="${esc(v.breed || "")}"></div>
      <div><label class="field">${t("dob")}</label><input id="a-dob" placeholder="2023-08" value="${esc(v.dob || "")}"></div>
    </div>
    <label class="field">${t("status")}</label>
    <select id="a-status">${["active", "sold", "deceased"].map(s => `<option value="${s}" ${v.status === s ? "selected" : ""}>${t(s)}</option>`).join("")}</select>
    <label class="field">${t("notes")}</label><textarea id="a-notes">${esc(v.notes || "")}</textarea>
    ${a ? `<label class="field">${t("photo")}</label><input type="file" accept="image/*" id="a-photo" onchange="uploadPhoto(${a.id})">` : ""}
    <button class="btn-primary" onclick="saveAnimal(${a ? a.id : "null"})">${t("save")}</button>`);
}

async function saveAnimal(id) {
  const payload = {
    tag: val("a-tag"), name: val("a-name"), species: val("a-species"),
    sex: val("a-sex"), breed: val("a-breed"), dob: val("a-dob"),
    status: val("a-status") || "active", notes: val("a-notes"),
  };
  await post(id ? `/api/animals/${id}?user_id=${userId}` : `/api/animals?user_id=${userId}`, payload);
  closeModal(); toast("✅ " + t("saved")); await refreshAll();
}

async function uploadPhoto(animalId) {
  const f = document.getElementById("a-photo").files[0];
  if (!f) return;
  const fd = new FormData(); fd.append("file", f);
  await fetch(`/api/animals/${animalId}/photo?user_id=${userId}`, { method: "POST", body: fd });
  toast("📷 " + t("saved")); await refreshAll();
}

async function openAnimalDetail(id) {
  const a = state.animals.find(x => x.id === id); if (!a) return;
  let events = [];
  try { events = await api(`/api/animals/${id}/events?user_id=${userId}`); } catch {}
  showModal(`
    <div class="modal-head"><h3>${SPECIES_ICON[a.species] || "🐾"} ${esc(a.tag || a.name || "#" + a.id)}</h3>
      <button class="modal-close" onclick="closeModal()">×</button></div>
    ${a.photo_path ? `<img src="${esc(a.photo_path)}" style="width:100%;border-radius:14px;margin-bottom:14px;max-height:230px;object-fit:cover;">` : ""}
    <div class="card" style="padding:14px;">
      ${[[t("name"), a.name], [t("breed"), a.breed], [t("sex"), a.sex ? t(a.sex) : ""], [t("dob"), a.dob], [t("status"), t(a.status)]]
        .filter(([, v]) => v).map(([k, v]) => `<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:var(--text-light);font-weight:650;">${k}</span><span style="font-weight:700;">${esc(v)}</span></div>`).join("")}
      ${a.notes ? `<div style="margin-top:10px;font-size:13.5px;color:var(--text-light);line-height:1.5;">${esc(a.notes)}</div>` : ""}
    </div>
    <div class="section-label">${t("history")}</div>
    ${events.length ? events.map(e => `<div class="event-row"><div class="event-main">
        <div class="event-desc">${esc(e.description || e.event_type)}</div>
        <div class="event-meta">${e.event_date || e.due_date || ""} · ${esc(e.event_type)}</div></div></div>`).join("")
      : `<div class="empty">—</div>`}
    <button class="btn-primary" style="margin-top:14px;" onclick="openEventModal(${a.id})">${t("add_event")}</button>
    <button class="btn-primary btn-secondary" onclick='openAnimalModal(${JSON.stringify(a).replace(/'/g, "&#39;")})'>${t("save")}</button>`);
}

function openEventModal(animalId = null) {
  const types = ["vaccination", "treatment", "birth", "sale", "death", "weight", "note"];
  showModal(`
    <div class="modal-head"><h3>${t("add_event")}</h3><button class="modal-close" onclick="closeModal()">×</button></div>
    <label class="field">${t("event_type")}</label>
    <select id="e-type">${types.map(x => `<option value="${x}">${x}</option>`).join("")}</select>
    <label class="field">${t("description")}</label><textarea id="e-desc"></textarea>
    <label class="field">${t("due_date")}</label><input type="date" id="e-due">
    ${animalId ? "" : `<label class="field">${t("tag")}</label>
      <select id="e-animal"><option value="">— ${t("nav_herd")} —</option>
      ${state.animals.map(a => `<option value="${a.id}">${esc(a.tag || a.name || "#" + a.id)}</option>`).join("")}</select>`}
    <button class="btn-primary" onclick="saveEvent(${animalId})">${t("save")}</button>`);
}

async function saveEvent(animalId) {
  const due = val("e-due");
  const body = {
    event_type: val("e-type"), description: val("e-desc"),
    animal_id: animalId || (val("e-animal") ? parseInt(val("e-animal")) : null),
    due_date: due || null,
  };
  await post(`/api/events?user_id=${userId}`, body);
  closeModal(); toast("✅ " + t("saved")); await refreshAll();
}

function exportCsv() { window.location = `/api/export/herd.csv?user_id=${userId}`; }

/* ─────────────── notebook scan ─────────────── */
function openScan() {
  showModal(`
    <div class="modal-head"><h3>📓 ${t("scan_title")}</h3><button class="modal-close" onclick="closeModal()">×</button></div>
    <p class="subtitle">${t("scan_sub")}</p>
    <input type="file" accept="image/*" capture="environment" id="scan-file" onchange="runScan()">
    <div id="scan-out"></div>`);
}

async function runScan() {
  const f = document.getElementById("scan-file").files[0]; if (!f) return;
  const out = document.getElementById("scan-out");
  out.innerHTML = `<div class="empty">${t("scan_reading")}</div>`;
  const fd = new FormData(); fd.append("file", f);
  try {
    const res = await fetch("/api/scan_notebook", { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    if (!data.animals?.length) { out.innerHTML = `<div class="empty">${t("scan_none")}</div>`; return; }
    window._scanned = data.animals.map(a => ({ ...a, events: (data.events || []).filter(e => e.animal_tag && e.animal_tag === a.tag) }));
    out.innerHTML = `<div class="section-label">${t("scan_review")} (${window._scanned.length})</div>` +
      window._scanned.map((a, i) => `
        <div class="card" style="padding:13px;">
          <div class="row-2">
            <div><label class="field">${t("tag")}</label><input value="${esc(a.tag || "")}" oninput="_scanned[${i}].tag=this.value"></div>
            <div><label class="field">${t("species")}</label>
              <select onchange="_scanned[${i}].species=this.value">
                ${["cattle", "goat", "sheep", "other"].map(s => `<option value="${s}" ${a.species === s ? "selected" : ""}>${SPECIES_ICON[s]} ${s}</option>`).join("")}
              </select></div>
          </div>
          <div class="row-2">
            <div><label class="field">${t("name")}</label><input value="${esc(a.name || "")}" oninput="_scanned[${i}].name=this.value"></div>
            <div><label class="field">${t("breed")}</label><input value="${esc(a.breed || "")}" oninput="_scanned[${i}].breed=this.value"></div>
          </div>
          ${a.notes ? `<div style="font-size:12.5px;color:var(--text-light);margin-top:6px;">${esc(a.notes)}</div>` : ""}
        </div>`).join("") +
      `<button class="btn-primary" onclick="confirmScan()">${t("scan_confirm")}</button>`;
  } catch (e) {
    let msg = String(e.message || e); try { msg = JSON.parse(msg).detail || msg; } catch {}
    out.innerHTML = `<div class="empty">${esc(msg)}</div>`;
  }
}

async function confirmScan() {
  await post(`/api/scan_notebook/confirm?user_id=${userId}`, { animals: window._scanned });
  closeModal(); toast(`✅ ${window._scanned.length} ${t("stat_animals").toLowerCase()}`); await refreshAll();
}

/* ─────────────── chat ─────────────── */
function buildChips() {
  document.getElementById("chips-row").innerHTML = CHIP_KEYS.map(k =>
    `<div class="chip" onclick="askChip('${k}')">${t(k)}</div>`).join("");
}
function askChip(key) { document.getElementById("chat-input").value = t(key); sendChat(); }

function renderChatGreeting(fresh = false) {
  const chat = document.getElementById("chat");
  if (chat.children.length && !fresh) return;
  chat.innerHTML = `<div class="msg bot">${esc(t("chat_greeting"))}</div>`;
  loadChatHistory();
}

async function loadChatHistory() {
  try {
    const msgs = await api(`/api/chat_history?user_id=${userId}` + (state.chatId ? `&chat_id=${state.chatId}` : ''));
    cache.set("chat", msgs);
    msgs.forEach(m => appendMsg(m.content, m.role === "user" ? "user" : "bot", [], true));
  } catch {
    (cache.get("chat", []) || []).forEach(m => appendMsg(m.content, m.role === "user" ? "user" : "bot", [], true));
  }
}

const VERDICTS = { GREEN: ["green", "verdict_green"], AMBER: ["amber", "verdict_amber"], RED: ["red", "verdict_red"] };

function appendMsg(text, sender, trace = [], skipExtras = false) {
  const chat = document.getElementById("chat");
  const el = document.createElement("div");
  el.className = "msg " + sender;
  let body = text || "";
  let verdictHtml = "";
  const vm = body.match(/\[(GREEN|AMBER|RED)\]/i);
  if (vm && sender === "bot") {
    const [cls, key] = VERDICTS[vm[1].toUpperCase()];
    verdictHtml = `<div class="verdict ${cls}">${cls === "green" ? "🟢" : cls === "amber" ? "🟡" : "🔴"} ${t(key)}</div>`;
    // Models sometimes still write the label after the marker ("[GREEN] fine"),
    // which would show the verdict twice. Drop it; the pill already says it.
    body = body
      .replace(new RegExp(`\\[${vm[1]}\\]\\s*(looking good|watch closely|act now|fine|good|ok(ay)?|caution|urgent)?[.:]?`, "i"), "")
      .trim();
    // A marker on a non-judgement answer (a saved record, a price) is noise.
    if (/^(i'?ve |i have |recorded|saved|noted|done)/i.test(body)) verdictHtml = "";
  }
  const html = esc(body).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br>");
  el.innerHTML = verdictHtml + html +
    (sender === "bot" && !skipExtras ? renderTrace(trace) + renderMsgActions(body) : "");
  chat.appendChild(el);
  setTimeout(() => { chat.scrollTop = chat.scrollHeight; }, 40);
  return el;
}

function renderMsgActions(text) {
  const safe = text.replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/\n/g, " ").slice(0, 900);
  return `<div class="msg-actions"><button class="msg-act speak-btn" onclick="speak('${safe}', this)">🔊 ${t("speak")}</button></div>`;
}

const TOOL_LABEL = {
  query_rangeland: "Checked rangeland monitoring sites",
  compare_seasons: "Compared REAL field measurements year-over-year",
  get_rainfall: "Fused Open-Meteo + NASA POWER rainfall",
  estimate_grazing_days: "Calculated grazing days from your herd",
  get_herd_summary: "Read your herd register",
  search_animals: "Searched your animals",
  get_upcoming_tasks: "Checked your health calendar",
  log_livestock_event: "Saved a record to your farm register",
  register_animal: "Added an animal to your register",
};

function renderTrace(trace) {
  if (!trace?.length) return "";
  const items = trace.map(t0 => {
    let facts = "";
    try {
      const r = JSON.parse(t0.content);
      const picks = [];
      if (r.summary) {
        picks.push(`grass ${r.summary.avg_grass_biomass_kg_ha} kg/ha`,
                   `cover ${r.summary.avg_veg_cover_pct}%`,
                   `capacity ${r.summary.avg_carrying_capacity_ha_per_lsu} ha/LSU`);
      }
      if (r.rain_60_mm != null) picks.push(`60-day rain ${r.rain_60_mm} mm`);
      if (r.range_60d_mm) picks.push(`60-day rain ${r.range_60d_mm} mm`);
      if (r.anomaly_vs_normal_pct != null) picks.push(`${r.anomaly_vs_normal_pct > 0 ? "+" : ""}${r.anomaly_vs_normal_pct}% vs normal`);
      if (r.confidence) picks.push(r.confidence);
      if (r.days_remaining != null) picks.push(`${r.days_remaining} grazing days`);
      if (r.total_lsu != null) picks.push(`${r.total_animals} animals, ${r.total_lsu} LSU`);
      if (r.count != null) picks.push(`${r.count} tasks`);
      if (r.matches != null) picks.push(`${r.matches} matches`);
      if (r.sites?.[0]?.same_season_comparison) picks.push(`site ${r.sites[0].site}, Feb-23 vs Feb-24`);
      if (r.data_source) picks.push(r.data_source.slice(0, 70));
      if (r.saved) picks.push("saved ✓");
      if (r.error) picks.push("⚠️ " + r.error.slice(0, 60));
      facts = picks.slice(0, 4).join(" · ");
    } catch {}
    return `<div class="trace-item"><b>${TOOL_LABEL[t0.name] || t0.name}</b>${facts ? "<br>" + esc(facts) : ""}</div>`;
  }).join("");
  return `<details class="trace"><summary>${t("reasoning")}</summary>${items}</details>`;
}

async function sendChat(fromVoice = false) {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text || !userId) return;
  input.value = "";
  appendMsg(text, "user");

  if (!navigator.onLine) { appendMsg(t("offline_chat"), "bot", [], true); return; }

  const chat = document.getElementById("chat");
  const loading = document.createElement("div");
  loading.className = "msg bot"; loading.textContent = t("thinking");
  chat.appendChild(loading); chat.scrollTop = chat.scrollHeight;

  try {
    const data = await api("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, user_id: parseInt(userId),
                             chat_id: state.chatId, lang: LANG }),
    });
    loading.remove();
    if (data.chat_id) state.chatId = data.chat_id;
    appendMsg(data.text, "bot", data.trace || []);
    const auto = localStorage.getItem("veldwys_autospeak") === "true";
    if (fromVoice || auto) speak(data.text.replace(/\[(GREEN|AMBER|RED)\]/i, ""));
    refreshAll();
  } catch (e) {
    loading.remove();
    appendMsg(t("offline_chat"), "bot", [], true);
  }
}

/* ─────────────── voice ─────────────── */
/* One audio channel for the whole app. Tapping Listen while something is loading or
   playing stops it rather than stacking a second voice on top. */
let audioToken = 0;
let speakingBtn = null;

function voicePrefs() {
  return {
    gender: localStorage.getItem("veldwys_voice_gender") || state.profile?.voice_gender || "female",
    speed: parseFloat(localStorage.getItem("veldwys_voice_speed") || state.profile?.voice_speed || 1.0),
  };
}

function stopSpeaking() {
  audioToken++;                       // invalidates any in-flight request
  if (currentAudio) { currentAudio.pause(); currentAudio.src = ""; currentAudio = null; }
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  if (speakingBtn) { setSpeakBtn(speakingBtn, "idle"); speakingBtn = null; }
}

function setSpeakBtn(btn, mode) {
  if (!btn) return;
  const label = { idle: `🔊 ${t("speak")}`, loading: `<span class="spinner dark"></span> ${t("speak")}`, playing: `⏹ ${t("stop_speak")}` }[mode];
  btn.innerHTML = label;
  btn.classList.toggle("on", mode === "playing");
}

async function speak(text, btn = null) {
  const wasPlayingThis = speakingBtn === btn && btn !== null;
  stopSpeaking();
  if (wasPlayingThis) return;                     // second tap = stop, don't restart

  const clean = String(text).replace(/\*\*/g, "").replace(/\[(GREEN|AMBER|RED)\]/gi, "").trim();
  if (!clean) return;
  const token = ++audioToken;
  const { gender, speed } = voicePrefs();
  speakingBtn = btn; setSpeakBtn(btn, "loading");

  try {
    const res = await fetch("/api/tts", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: clean, lang: LANG, gender }),
    });
    if (!res.ok) throw new Error("tts");
    const blob = await res.blob();
    if (token !== audioToken) return;             // user moved on while we were fetching
    currentAudio = new Audio(URL.createObjectURL(blob));
    currentAudio.playbackRate = speed;
    currentAudio.onended = () => { if (token === audioToken) { setSpeakBtn(btn, "idle"); speakingBtn = null; } };
    setSpeakBtn(btn, "playing");
    await currentAudio.play();
  } catch {
    if (token !== audioToken) return;
    if ("speechSynthesis" in window) {            // offline / API failure fallback
      const u = new SpeechSynthesisUtterance(clean);
      u.lang = { af: "af-ZA", en: "en-ZA", ng: "en-ZA", kj: "en-ZA" }[LANG] || "en-ZA";
      u.rate = speed;
      u.onend = () => { setSpeakBtn(btn, "idle"); speakingBtn = null; };
      speechSynthesis.speak(u);
      setSpeakBtn(btn, "playing");
    } else { setSpeakBtn(btn, "idle"); speakingBtn = null; }
  }
}

let mediaRecorder, audioChunks = [], isRecording = false;
const micBtn = document.getElementById("mic-btn");

async function startRecording(e) {
  if (e) e.preventDefault();
  if (isRecording) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = ev => audioChunks.push(ev.data);
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t0 => t0.stop());
      await transcribe(new Blob(audioChunks, { type: "audio/webm" }));
    };
    mediaRecorder.start();
    isRecording = true;
    micBtn.classList.add("recording");
    document.getElementById("chat-input").placeholder = t("listening");
  } catch {
    toast("🎤 " + (location.protocol === "https:" ? "Microphone blocked" : "Microphone needs HTTPS"));
  }
}

function stopRecording(e) {
  if (e) e.preventDefault();
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop(); isRecording = false;
    micBtn.classList.remove("recording");
    document.getElementById("chat-input").placeholder = t("transcribing");
  }
}

async function transcribe(blob) {
  const fd = new FormData(); fd.append("file", blob, "audio.webm");
  try {
    const res = await fetch("/api/transcribe", { method: "POST", body: fd });
    const data = await res.json();
    document.getElementById("chat-input").value = data.text || "";
    document.getElementById("chat-input").placeholder = t("chat_ph");
    if (data.text) sendChat(true);
  } catch {
    document.getElementById("chat-input").placeholder = t("chat_ph");
    toast("🎤 ✗");
  }
}

micBtn.addEventListener("mousedown", startRecording);
micBtn.addEventListener("mouseup", stopRecording);
micBtn.addEventListener("mouseleave", () => { if (isRecording) stopRecording(); });
micBtn.addEventListener("touchstart", startRecording, { passive: false });
micBtn.addEventListener("touchend", stopRecording, { passive: false });

/* ─────────────── chats ─────────────── */
async function loadChats() {
  try { state.chats = await api(`/api/chats?user_id=${userId}`); cache.set("chats", state.chats); }
  catch { state.chats = cache.get("chats", []); }
  const cur = state.chats.find(c => c.id === state.chatId) || state.chats[0];
  if (cur) state.chatId = cur.id;
  document.getElementById("chat-title").textContent = cur?.title || t("chat_new");
}

async function startNewChat() {
  stopConversation();
  try {
    const r = await post(`/api/chats?user_id=${userId}`, {}, false);
    state.chatId = r.id;
  } catch { state.chatId = null; }
  document.getElementById("chat").innerHTML = "";
  document.getElementById("chat-title").textContent = t("chat_new");
  renderChatGreeting(true);
  await loadChats();
}

async function openChatDrawer(query = "") {
  await loadChats();
  const list = state.chats.filter(c =>
    !query || (c.title || "").toLowerCase().includes(query.toLowerCase()) ||
    (c.preview || "").toLowerCase().includes(query.toLowerCase()));
  showModal(`
    <div class="modal-head"><h3>${t("chats_title")}</h3><button class="modal-close" onclick="closeModal()">×</button></div>
    <input type="text" id="chat-search" placeholder="${t("chats_search")}" value="${esc(query)}"
           oninput="searchChats(this.value)">
    <button class="btn-primary" onclick="closeModal();startNewChat();">✚ ${t("chat_new")}</button>
    <div id="chat-list">${list.length ? list.map(c => `
      <div class="chat-item ${c.id === state.chatId ? "on" : ""}" onclick="openChat(${c.id})">
        <div class="chat-item-main">
          <div class="chat-item-title">${esc(c.title || t("chat_new"))}</div>
          <div class="chat-item-prev">${esc((c.preview || "").slice(0, 70))}</div>
        </div>
        <button class="icon-btn" onclick="event.stopPropagation();removeChat(${c.id})">🗑</button>
      </div>`).join("") : `<div class="empty">${t("chats_none")}</div>`}</div>`);
}

let searchTimer;
function searchChats(q) {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    try {
      const res = await api(`/api/chats?user_id=${userId}&q=${encodeURIComponent(q)}`);
      document.getElementById("chat-list").innerHTML = res.length ? res.map(c => `
        <div class="chat-item ${c.id === state.chatId ? "on" : ""}" onclick="openChat(${c.id})">
          <div class="chat-item-main">
            <div class="chat-item-title">${esc(c.title || t("chat_new"))}</div>
            <div class="chat-item-prev">${esc((c.preview || "").slice(0, 70))}</div>
          </div>
          <button class="icon-btn" onclick="event.stopPropagation();removeChat(${c.id})">🗑</button>
        </div>`).join("") : `<div class="empty">${t("chats_none")}</div>`;
    } catch {}
  }, 250);
}

async function openChat(id) {
  stopConversation();
  state.chatId = id;
  closeModal();
  document.getElementById("chat").innerHTML = "";
  const c = state.chats.find(x => x.id === id);
  document.getElementById("chat-title").textContent = c?.title || t("chat_new");
  renderChatGreeting(true);
}

async function removeChat(id) {
  await fetch(`/api/chats/${id}?user_id=${userId}`, { method: "DELETE" });
  if (state.chatId === id) { state.chatId = null; document.getElementById("chat").innerHTML = ""; }
  openChatDrawer();
}

/* ─────────────── documents ─────────────── */
async function uploadDoc() {
  const f = document.getElementById("doc-file").files[0];
  if (!f) return;
  toast("📎 " + t("doc_reading"));
  const fd = new FormData(); fd.append("file", f);
  try {
    const res = await fetch(`/api/documents?user_id=${userId}`, { method: "POST", body: fd });
    if (!res.ok) throw new Error((await res.json()).detail);
    const d = await res.json();
    appendMsg(`📎 ${d.filename}`, "user");
    appendMsg(t("doc_saved").replace("{name}", d.filename), "bot", [], true);
    loadDocs();
  } catch (e) { toast("⚠️ " + String(e.message || e).slice(0, 80)); }
  document.getElementById("doc-file").value = "";
}

async function loadDocs() {
  const el = document.getElementById("docs-list");
  if (!el) return;
  try {
    const docs = await api(`/api/documents?user_id=${userId}`);
    state.docs = docs;
    el.innerHTML = docs.length ? docs.map(d => `
      <div class="event-row"><div class="event-main">
        <div class="event-desc">📄 ${esc(d.filename)}</div>
        <div class="event-meta">${esc((d.preview || "").slice(0, 60))}</div>
      </div><button class="icon-btn" onclick="removeDoc(${d.id})">🗑</button></div>`).join("")
      : `<div class="empty" style="padding:16px;">${t("docs_none")}</div>`;
  } catch {}
}

async function removeDoc(id) {
  await fetch(`/api/documents/${id}?user_id=${userId}`, { method: "DELETE" });
  loadDocs();
}

/* ─────────────── conversation mode ─────────────── */
/* Hands-free loop: listen, detect the pause, answer, speak, listen again.
   Voice activity is plain RMS over the WebAudio analyser. A wasm VAD (Silero) would
   be more robust, but it needs remote assets and this app has to work offline. */
let convo = { on: false, ctx: null, stream: null, rec: null, chunks: [], timer: null };

function toggleConversation() { convo.on ? stopConversation() : startConversation(); }

async function startConversation() {
  try {
    convo.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    toast("🎤 " + (location.protocol === "https:" ? t("mic_blocked") : t("mic_https")));
    return;
  }
  convo.on = true;
  document.getElementById("convo-btn").classList.add("on");
  const status = document.getElementById("convo-status");
  status.classList.add("on");
  convoListen();
}

function stopConversation() {
  convo.on = false;
  clearInterval(convo.timer);
  try { convo.rec && convo.rec.state !== "inactive" && convo.rec.stop(); } catch {}
  convo.stream?.getTracks().forEach(t0 => t0.stop());
  convo.ctx?.close().catch(() => {});
  convo.ctx = null; convo.stream = null;
  document.getElementById("convo-btn")?.classList.remove("on");
  document.getElementById("convo-status")?.classList.remove("on");
  stopSpeaking();
}

function convoStatus(key) {
  const el = document.getElementById("convo-status");
  if (el) el.textContent = t(key);
}

async function convoListen() {
  if (!convo.on) return;
  convoStatus("listening");
  convo.ctx = convo.ctx || new (window.AudioContext || window.webkitAudioContext)();
  const src = convo.ctx.createMediaStreamSource(convo.stream);
  const analyser = convo.ctx.createAnalyser();
  analyser.fftSize = 1024;
  src.connect(analyser);
  const buf = new Uint8Array(analyser.fftSize);

  convo.rec = new MediaRecorder(convo.stream);
  convo.chunks = [];
  convo.rec.ondataavailable = e => convo.chunks.push(e.data);
  convo.rec.onstop = async () => {
    src.disconnect();
    if (!convo.on) return;
    const blob = new Blob(convo.chunks, { type: "audio/webm" });
    if (blob.size < 3000) return convoListen();          // nothing but room noise
    convoStatus("transcribing");
    const fd = new FormData(); fd.append("file", blob, "a.webm");
    try {
      const r = await (await fetch("/api/transcribe", { method: "POST", body: fd })).json();
      if (!r.text?.trim()) return convoListen();
      document.getElementById("chat-input").value = r.text;
      convoStatus("thinking");
      await sendChat(true);                              // speaks the reply
      if (convo.on) {
        const wait = setInterval(() => {
          if (!currentAudio || currentAudio.ended || currentAudio.paused) {
            clearInterval(wait); convoListen();
          }
        }, 350);
      }
    } catch { convoListen(); }
  };
  convo.rec.start();

  let spoke = false, quietFor = 0, elapsed = 0;
  clearInterval(convo.timer);
  convo.timer = setInterval(() => {
    if (!convo.on) return clearInterval(convo.timer);
    analyser.getByteTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v; }
    const rms = Math.sqrt(sum / buf.length);
    elapsed += 100;
    if (rms > 0.045) { spoke = true; quietFor = 0; } else if (spoke) { quietFor += 100; }
    // Stop 1.2s after they stop talking, or bail if they never started.
    if ((spoke && quietFor > 1200) || (!spoke && elapsed > 9000) || elapsed > 30000) {
      clearInterval(convo.timer);
      try { convo.rec.state !== "inactive" && convo.rec.stop(); } catch {}
    }
  }, 100);
}

/* ─────────────── retranslate visible chat ─────────────── */
async function retranslateChat() {
  const nodes = [...document.querySelectorAll("#chat .msg")];
  if (!nodes.length || !navigator.onLine) return;
  const texts = nodes.map(n => n.dataset.raw || n.innerText.trim()).filter(Boolean);
  if (!texts.length) return;
  try {
    const r = await post("/api/translate_chat", { texts, lang: LANG }, false);
    r.texts.forEach((tx, i) => {
      const n = nodes[i]; if (!n || !tx) return;
      if (!n.dataset.raw) n.dataset.raw = texts[i];
      const isBot = n.classList.contains("bot");
      const trace = n.querySelector(".trace")?.outerHTML || "";
      const acts = isBot ? renderMsgActions(tx) : "";
      n.innerHTML = esc(tx).replace(/\n/g, "<br>") + trace + acts;
    });
  } catch {}
}

/* ─────────────── settings ─────────────── */
function saveVoicePrefs() {
  const g = document.getElementById("p-voice-gender")?.value || "female";
  const s = document.getElementById("p-voice-speed")?.value || "1";
  localStorage.setItem("veldwys_voice_gender", g);
  localStorage.setItem("veldwys_voice_speed", s);
}

function testVoice() { speak(t("voice_sample")); }

function profilePayload() {
  return {
    farm_name: val("p-farmname"),
    full_name: val("p-fullname"),
    role: val("p-role"),
    lat: parseFloat(val("p-lat")) || null,
    lon: parseFloat(val("p-lon")) || null,
    camp_area_ha: parseFloat(val("p-area")) || 0,
    cattle_count: parseInt(val("p-cattle")) || 0,
    goat_count: parseInt(val("p-goats")) || 0,
    sheep_count: parseInt(val("p-sheep")) || 0,
    language: LANG,
    voice_gender: localStorage.getItem("veldwys_voice_gender") || "female",
    voice_speed: parseFloat(localStorage.getItem("veldwys_voice_speed") || "1"),
  };
}

function renderProfileForm() {
  const p = state.profile; if (!p) return;
  set("p-farmname", p.farm_name || ""); set("p-fullname", p.full_name || "");
  set("p-lat", p.lat ?? ""); set("p-lon", p.lon ?? "");
  set("p-area", p.camp_area_ha || ""); set("p-cattle", p.cattle_count || "");
  set("p-goats", p.goat_count || ""); set("p-sheep", p.sheep_count || "");
  const roleSel = document.getElementById("p-role");
  if (roleSel) roleSel.value = p.role || "owner";
  const langSel = document.getElementById("p-lang"); if (langSel) langSel.value = LANG;

  const { gender, speed } = voicePrefs();
  const gSel = document.getElementById("p-voice-gender"); if (gSel) gSel.value = gender;
  const sIn = document.getElementById("p-voice-speed");
  if (sIn) { sIn.value = speed; document.getElementById("speed-val").textContent = (+speed).toFixed(2) + "×"; }
  const auto = document.getElementById("autospeak");
  if (auto) auto.checked = localStorage.getItem("veldwys_autospeak") === "true";
  if (p.lat && p.lon) showRegion(false, p.lat, p.lon);

  // Identity card
  const name = p.full_name || p.username || "";
  const initials = (name.trim().split(/\s+/).map(w => w[0]).join("").slice(0, 2) || "?").toUpperCase();
  const av = document.getElementById("p-avatar"); if (av) av.textContent = initials;
  const dn = document.getElementById("p-display-name");
  if (dn) dn.textContent = name || t("your_name");
  const dm = document.getElementById("p-display-meta");
  if (dm) {
    const role = p.role ? t("role_" + p.role) : "";
    const since = (p.created_at || "").slice(0, 10);
    dm.textContent = [role, p.farm_name, p.region, since ? `${t("since")} ${since}` : ""]
      .filter(Boolean).join(" · ");
  }

  // Herd from the register, read-only. The editable numbers below are only the
  // starting counts, which is what confused things before.
  const herd = p.herd || {};
  const ro = document.getElementById("p-herd-readout");
  if (ro) {
    const counts = herd.counts || {};
    ro.innerHTML = Object.keys(counts).length
      ? Object.entries(counts).map(([sp, n]) =>
          `<span>${SPECIES_ICON[sp] || "🐾"} ${n} ${t(sp === "cattle" ? "cattle" : sp === "goat" ? "goats" : sp === "sheep" ? "sheep" : "species")}</span>`).join("") +
        `<span>⚖️ ${herd.total_lsu} LSU</span>`
      : `<span>${t("herd_empty")}</span>`;
  }
  set2("p-stat-animals", herd.total_animals || 0);
  set2("p-stat-events", (state.events || []).length + (p.events_total || 0));
  set2("p-stat-chats", (state.chats || []).length);
}
function set2(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

async function saveProfile() {
  await post(`/api/profile?user_id=${userId}`, profilePayload());
  toast("✅ " + t("saved"));
  await refreshAll();
}

/* ─────────────── analytics ─────────────── */
/* Palette validated for colour-blind separation (protan/deutan/tritan) before use.
   Order matters: green and orange sit apart because that pair is the protan weak spot. */
const C = { green: "#2f6d3a", blue: "#5b9bd5", orange: "#d4761a", purple: "#8b4a94",
            grid: "rgba(0,0,0,.09)", ink: "#736d60" };

async function refreshAnalytics() {
  const box = document.getElementById("analytics-body");
  const cached = cache.get("analytics");
  if (cached) renderAnalytics(cached); else box.innerHTML = `<div class="empty">…</div>`;
  try {
    const data = await api(`/api/analytics?user_id=${userId}`);
    cache.set("analytics", data);
    renderAnalytics(data);
  } catch {
    if (!cached) box.innerHTML = `<div class="empty">${t("offline_chat")}</div>`;
  }
}

function renderAnalytics(d) {
  const box = document.getElementById("analytics-body");
  const m = d.movement || {}, h = d.health || {}, s = d.structure || {},
        g = d.grazing || {}, r = d.rainfall || {}, p = d.pasture || {};

  // Stocking vs the regional guideline is the number this whole hackathon is about.
  const stock = g.stocking_vs_guideline_pct;
  const stockCls = stock == null ? "" : stock > 110 ? "bad" : stock > 90 ? "warn" : "good";
  const compl = h.compliance_pct;
  const complCls = compl == null ? "" : compl >= 80 ? "good" : compl >= 50 ? "warn" : "bad";

  box.innerHTML = `
    <div class="kpi-grid">
      ${kpi(stock == null ? "—" : stock + "%", t("an_stocking"), stockCls,
            g.ha_per_lsu ? `${g.ha_per_lsu} ha/LSU ${t("an_vs")} ${g.guideline_ha_per_lsu} ${t("an_guideline")}` : "")}
      ${kpi(compl == null ? "—" : compl + "%", t("an_compliance"), complCls,
            h.overdue ? `${h.overdue} ${t("an_overdue")}` : t("an_uptodate"))}
      ${kpi((m.net_change > 0 ? "+" : "") + (m.net_change ?? 0), t("an_net"), m.net_change >= 0 ? "good" : "warn",
            `${m.total_births || 0} ${t("an_births")} · ${m.total_sales || 0} ${t("an_sales")} · ${m.total_deaths || 0} ${t("an_deaths")}`)}
      ${kpi(m.mortality_pct == null ? "—" : m.mortality_pct + "%", t("an_mortality"),
            m.mortality_pct > 5 ? "bad" : "good", t("an_mortality_sub"))}
    </div>

    ${g.capacity_lsu ? chartCard(t("an_capacity"), t("an_capacity_note"), gaugeSvg(g)) : ""}
    ${m.labels?.length ? chartCard(t("an_movement"), t("an_movement_note"), movementSvg(m),
        legend([[C.green, t("an_births")], [C.orange, t("an_sales")], [C.purple, t("an_deaths")]])) : ""}
    ${m.total_revenue ? chartCard(t("an_revenue"), t("an_revenue_note"), revenueSvg(m)) : ""}
    ${p.labels?.length ? chartCard(t("an_pasture") + ` (${p.site})`, p.source, pastureSvg(p),
        legend([[C.green, t("an_grass")], [C.orange, t("an_bare")], [C.purple, t("an_woody")]])) : ""}
    ${r.rain_60_mm != null ? chartCard(t("an_rain"), r.confidence || "", rainSvg(r)) : ""}
    ${s.total_active ? chartCard(t("an_structure"), t("an_structure_note"), structureHtml(s)) : ""}
  `;
}

const kpi = (val, lbl, cls = "", sub = "") =>
  `<div class="kpi"><div class="k-val ${cls}">${esc(val)}</div><div class="k-lbl">${esc(lbl)}</div>${sub ? `<div class="k-sub">${esc(sub)}</div>` : ""}</div>`;
const chartCard = (title, note, svg, leg = "") =>
  `<div class="chart-card"><div class="chart-title">${esc(title)}</div>${note ? `<div class="chart-note">${esc(note)}</div>` : ""}${svg}${leg}</div>`;
const legend = (items) =>
  `<div class="legend">${items.map(([c, l]) => `<span><i style="background:${c}"></i>${esc(l)}</span>`).join("")}</div>`;

/** Horizontal capacity bar: where this herd sits against what the region carries. */
function gaugeSvg(g) {
  const cap = g.capacity_lsu || 1, have = g.lsu || 0;
  const pct = Math.min(140, (have / cap) * 100);
  const w = 320, barH = 26, y = 14;
  const fill = pct > 110 ? "#c0392b" : pct > 90 ? C.orange : C.green;
  return `<svg viewBox="0 0 ${w} 72" role="img" aria-label="Stocking versus capacity">
    <rect x="0" y="${y}" width="${w}" height="${barH}" rx="6" fill="rgba(0,0,0,.06)"/>
    <rect x="0" y="${y}" width="${Math.min(w, w * pct / 100)}" height="${barH}" rx="6" fill="${fill}"/>
    <line x1="${w / 1.4}" y1="${y - 5}" x2="${w / 1.4}" y2="${y + barH + 5}" stroke="${C.ink}" stroke-width="2" stroke-dasharray="3 3"/>
    <text x="4" y="${y + barH + 22}" font-size="11" fill="${C.ink}" font-weight="700">${have} LSU ${t("an_now")}</text>
    <text x="${w}" y="${y + barH + 22}" font-size="11" fill="${C.ink}" font-weight="700" text-anchor="end">${t("an_capacity_is")} ${cap} LSU</text>
    <text x="0" y="9" font-size="11" fill="${C.ink}" font-weight="700">${Math.round(pct)}% ${t("an_of_capacity")}</text>
  </svg>`;
}

/** Grouped bars, 12 months of herd movement. */
function movementSvg(m) {
  const w = 340, h = 130, pad = 22;
  const n = m.labels.length;
  const max = Math.max(1, ...m.births, ...m.sales, ...m.deaths);
  const slot = (w - pad) / n, bw = Math.max(3, slot / 4.2);
  const bars = m.labels.map((lab, i) => {
    const x0 = pad + i * slot + 2;
    return [[m.births[i], C.green, 0], [m.sales[i], C.orange, bw + 1], [m.deaths[i], C.purple, (bw + 1) * 2]]
      .map(([v, c, off]) => v ? `<rect x="${(x0 + off).toFixed(1)}" y="${(h - 18 - (v / max) * (h - 34)).toFixed(1)}" width="${bw.toFixed(1)}" height="${((v / max) * (h - 34)).toFixed(1)}" rx="2" fill="${c}"/>` : "")
      .join("") +
      `<text x="${(x0 + bw * 1.5).toFixed(1)}" y="${h - 5}" font-size="9" fill="${C.ink}" text-anchor="middle">${lab}</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Herd movement by month">
    <line x1="${pad}" y1="${h - 18}" x2="${w}" y2="${h - 18}" stroke="${C.grid}" stroke-width="1"/>
    <text x="0" y="16" font-size="10" fill="${C.ink}">${max}</text>
    ${bars}</svg>`;
}

function revenueSvg(m) {
  const w = 340, h = 110, pad = 30;
  const max = Math.max(1, ...m.revenue);
  const slot = (w - pad) / m.labels.length, bw = Math.max(6, slot * 0.6);
  const bars = m.revenue.map((v, i) => {
    const x = pad + i * slot + (slot - bw) / 2;
    const bh = (v / max) * (h - 34);
    return (v ? `<rect x="${x.toFixed(1)}" y="${(h - 18 - bh).toFixed(1)}" width="${bw.toFixed(1)}" height="${bh.toFixed(1)}" rx="3" fill="${C.green}"/>
      <text x="${(x + bw / 2).toFixed(1)}" y="${(h - 22 - bh).toFixed(1)}" font-size="9" fill="${C.ink}" text-anchor="middle" font-weight="700">${(v / 1000).toFixed(0)}k</text>` : "") +
      `<text x="${(x + bw / 2).toFixed(1)}" y="${h - 5}" font-size="9" fill="${C.ink}" text-anchor="middle">${m.labels[i]}</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Sales revenue by month">
    <line x1="${pad}" y1="${h - 18}" x2="${w}" y2="${h - 18}" stroke="${C.grid}"/>
    <text x="0" y="16" font-size="10" fill="${C.ink}">N$${(max / 1000).toFixed(0)}k</text>
    ${bars}</svg>`;
}

/** Real measured pasture change across the four field visits. */
function pastureSvg(p) {
  const w = 340, h = 140, padL = 26, padB = 26;
  const n = p.labels.length;
  const max = Math.max(40, ...[...p.grass_cover, ...p.bare_ground, ...p.woody_cover].filter(v => v != null));
  const X = i => padL + (i * (w - padL - 6)) / Math.max(1, n - 1);
  const Y = v => h - padB - (v / max) * (h - padB - 14);
  const line = (arr, color) => {
    const pts = arr.map((v, i) => v == null ? null : `${X(i).toFixed(1)},${Y(v).toFixed(1)}`).filter(Boolean);
    return `<polyline points="${pts.join(" ")}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>` +
      arr.map((v, i) => v == null ? "" : `<circle cx="${X(i).toFixed(1)}" cy="${Y(v).toFixed(1)}" r="4" fill="${color}" stroke="#fff" stroke-width="2"/>`).join("");
  };
  const labels = p.labels.map((l, i) =>
    `<text x="${X(i).toFixed(1)}" y="${h - 8}" font-size="9" fill="${C.ink}" text-anchor="middle">${esc(l.replace(" 20", " '"))}</text>`).join("");
  return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Pasture condition over field visits">
    ${[0, max / 2, max].map(v => `<line x1="${padL}" y1="${Y(v).toFixed(1)}" x2="${w}" y2="${Y(v).toFixed(1)}" stroke="${C.grid}"/>
       <text x="0" y="${(Y(v) + 3).toFixed(1)}" font-size="9" fill="${C.ink}">${Math.round(v)}%</text>`).join("")}
    ${line(p.grass_cover, C.green)}${line(p.bare_ground, C.orange)}${line(p.woody_cover, C.purple)}${labels}</svg>`;
}

function rainSvg(r) {
  const rows = [[t("an_r30"), r.rain_30_mm], [t("an_r60"), r.rain_60_mm],
                [t("an_r90"), r.rain_90_mm], [t("an_rnormal"), r.normal_60d_mm],
                [t("an_rforecast"), r.forecast_7d_mm]].filter(x => x[1] != null);
  const max = Math.max(1, ...rows.map(x => x[1]));
  const w = 340, rowH = 26;
  return `<svg viewBox="0 0 ${w} ${rows.length * rowH + 6}" role="img" aria-label="Rainfall">
    ${rows.map(([lab, v], i) => {
      const y = i * rowH + 4, bw = (v / max) * (w - 150);
      const c = lab === t("an_rnormal") ? C.purple : C.blue;
      return `<text x="0" y="${y + 14}" font-size="11" fill="${C.ink}" font-weight="650">${esc(lab)}</text>
        <rect x="96" y="${y + 4}" width="${Math.max(2, bw).toFixed(1)}" height="13" rx="3" fill="${c}"/>
        <text x="${(100 + Math.max(2, bw)).toFixed(1)}" y="${y + 15}" font-size="11" fill="${C.ink}" font-weight="700">${v} mm</text>`;
    }).join("")}</svg>`;
}

function structureHtml(s) {
  const total = s.total_active || 1;
  const order = [["cattle", C.green], ["goat", C.orange], ["sheep", C.purple]];
  const segs = order.filter(([sp]) => s.by_species[sp]).map(([sp, c]) => {
    const n = s.by_species[sp];
    return `<div style="flex:${n};background:${c};height:26px;" title="${sp}: ${n}"></div>`;
  }).join('<div style="width:2px;background:#fff;height:26px;"></div>');
  return `<div style="display:flex;border-radius:6px;overflow:hidden;margin-bottom:10px;">${segs}</div>
    ${legend(order.filter(([sp]) => s.by_species[sp]).map(([sp, c]) =>
      [c, `${t(sp === "cattle" ? "cattle" : sp === "goat" ? "goats" : "sheep")} ${s.by_species[sp]}`]))}
    <div class="k-sub" style="margin-top:10px;">
      ${s.female_pct_cattle != null ? `${s.female_pct_cattle}% ${t("an_female")} · ` : ""}
      ${s.avg_age_years != null ? `${t("an_avgage")} ${s.avg_age_years} · ` : ""}
      ${s.tagged_pct != null ? `${s.tagged_pct}% ${t("an_tagged")}` : ""}
    </div>`;
}

/* ─────────────── helpers ─────────────── */
function val(id) { return document.getElementById(id)?.value?.trim() || ""; }
function set(id, v) { const el = document.getElementById(id); if (el) el.value = v; }
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

/* ─────────────── boot ─────────────── */
(function boot() {
  applyI18n(); updateLangBadge(); buildLangGrid(); buildChips();
  setOnline(navigator.onLine);
  if (userId) {
    document.body.classList.add("authed");
    renderFromCache();
    switchView("dashboard");
    refreshAll();
  } else {
    toggleAuthMode(); toggleAuthMode();  // sets initial button labels
  }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
})();
