import React, { useState, useEffect, useCallback } from "react";
import { Search, MapPin, Bed, Users, CheckCircle2, ArrowLeft, LogOut } from "lucide-react";

/* ===================== API client (reusable) ===================== */
const DEFAULT_API = "https://mrsw-rentconnect.onrender.com";
const apiBase = () => (sessionStorage.getItem("mrsw_api") || DEFAULT_API).replace(/\/$/, "");
const Token = {
  get: () => sessionStorage.getItem("mrsw_token"),
  set: (t) => (t ? sessionStorage.setItem("mrsw_token", t) : sessionStorage.removeItem("mrsw_token")),
};

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && Token.get()) headers.Authorization = "Bearer " + Token.get();
  let res;
  try {
    res = await fetch(apiBase() + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw { message: `Can't reach the API at ${apiBase()}. The free backend sleeps after ~15 min idle — give it 30–60s and retry.` };
  }
  if (res.status === 401) { Token.set(null); throw { auth: true, message: "Please sign in again." }; }
  if (!res.ok) {
    let d; try { d = (await res.json()).detail; } catch {}
    throw { status: res.status, message: d || `Request failed (${res.status}).` };
  }
  if (res.status === 204) return null;
  return res.json();
}

const Api = {
  login: (email, password) => api("/auth/login", { method: "POST", auth: false, body: { email, password } }),
  register: (body) => api("/auth/register", { method: "POST", auth: false, body }),
  me: () => api("/auth/me"),
  listings: () => api("/listings", { auth: false }),
  listing: (id) => api("/listings/" + id, { auth: false }),
  createListing: (body) => api("/listings", { method: "POST", body }),
  myListings: () => api("/listings/mine"),
  book: (body) => api("/bookings", { method: "POST", body }),
  myBookings: () => api("/bookings/me"),
  incoming: () => api("/bookings/incoming"),
  setBooking: (id, status) => api(`/bookings/${id}/status`, { method: "PATCH", body: { status } }),
  tenant: () => api("/tenants/me"),
  wallet: () => api("/wallet"),
  txns: () => api("/wallet/transactions"),
  plan: () => api("/plans/me"),
  savePlan: (body) => api("/plans", { method: "POST", body }),
  projection: (amount, frequency) => api(`/plans/projection?amount=${encodeURIComponent(amount)}&frequency=${encodeURIComponent(frequency)}`),
  myLease: () => api("/leases/me"),
  maintenance: () => api("/maintenance"),
  createMaintenance: (body) => api("/maintenance", { method: "POST", body }),
  adminOverview: () => api("/admin/overview"),
  adminRisk: () => api("/admin/risk"),
  adminApprovals: () => api("/admin/approvals"),
  approveUser: (id) => api(`/admin/users/${id}/approve`, { method: "POST" }),
  properties: () => api("/properties"),
  createProperty: (body) => api("/properties", { method: "POST", body }),
  landlordLeases: () => api("/leases"),
  setMaintenance: (id, status) => api(`/maintenance/${id}/status`, { method: "PATCH", body: { status } }),
};

/* ===================== constants + helpers ===================== */
const ghs = (n) => "GHS " + Math.round(Number(n) || 0).toLocaleString("en-US");
const UNIS = ["University of Ghana", "KNUST", "University of Cape Coast", "University of Professional Studies (UPSA)"];
const ROOMS = ["1-in-1", "2-in-1", "3-in-1", "4-in-1"];

const BUCKETS = [
  { key: "stability_reserve", label: "Stability Reserve", color: "#0F4D38" },
  { key: "housing_savings", label: "Housing Savings", color: "#1F7A5C" },
  { key: "property_protection", label: "Property Protection", color: "#3E8E6F" },
  { key: "emergency_support", label: "Emergency Support", color: "#7FB39A" },
  { key: "ownership_fund", label: "Ownership Fund", color: "#B68A2E" },
];
const FACTORS = {
  contribution_consistency: "Contribution consistency", rent_payment_history: "Rent payment history",
  failed_deductions: "Successful deductions", wallet_growth: "Wallet growth",
  maintenance_behavior: "Maintenance behaviour", landlord_review: "Landlord review",
  dispute_history: "Dispute history", guarantor_strength: "Guarantor strength",
};
const LEVEL = {
  green: { fg: "var(--s-green-fg)", bg: "var(--s-green-bg)", label: "On track" },
  yellow: { fg: "var(--s-amber-fg)", bg: "var(--s-amber-bg)", label: "Watch" },
  orange: { fg: "var(--s-orange-fg)", bg: "var(--s-orange-bg)", label: "Elevated" },
  red: { fg: "var(--s-red-fg)", bg: "var(--s-red-bg)", label: "Distressed" },
};
const statusStyle = (s) =>
  s === "confirmed" ? { color: "var(--s-green-fg)", background: "var(--s-green-bg)" }
  : s === "cancelled" ? { color: "var(--s-red-fg)", background: "var(--s-red-bg)" }
  : { color: "var(--s-amber-fg)", background: "var(--s-amber-bg)" };
const fmtDate = (s) => { try { return new Date(s).toLocaleDateString(); } catch { return ""; } };
const urgencyStyle = (u) =>
  u === "emergency" ? { color: "var(--s-red-fg)", background: "var(--s-red-bg)" }
  : u === "high" ? { color: "var(--s-orange-fg)", background: "var(--s-orange-bg)" }
  : u === "low" ? { color: "var(--s-green-fg)", background: "var(--s-green-bg)" }
  : { color: "var(--s-amber-fg)", background: "var(--s-amber-bg)" };

/* ===================== small components ===================== */
function Loading({ label }) {
  return <div className="loading"><span className="spinner" />{label || "Loading…"}</div>;
}
function Field2({ label, children, full }) {
  return <div className={"f2" + (full ? " full" : "")}><label className="label">{label}</label>{children}</div>;
}
function Meter({ wallet }) {
  const target = wallet.target_amount || 0;
  return (
    <div className="meter">
      <div className="vessel"><div className="fill">
        {BUCKETS.map((b) => {
          const h = target > 0 ? Math.min(100, ((wallet[b.key] || 0) / target) * 100) : 0;
          return <div key={b.key} className="seg" style={{ height: h + "%", background: b.color }} />;
        })}
      </div></div>
      <div className="target"><b>Target {ghs(target)}</b></div>
    </div>
  );
}

/* ===================== header ===================== */
function Header({ user, view, go, signOut }) {
  return (
    <header className="bar"><div className="bar-in">
      <button className="brand" onClick={() => go("market")}>
        <div className="logo"><span className="disp">M</span></div>
        <div className="brandtext">
          <div className="bn disp">MRSW <span className="gold">RentConnect</span></div>
          <div className="bs">Campus hostels · Ghana</div>
        </div>
      </button>
      <nav className="nav">
        <button className={"navlink" + (view === "market" ? " on" : "")} onClick={() => go("market")}>Find a hostel</button>
        {user && user.role === "tenant" && <>
          <button className={"navlink" + (view === "tenant" ? " on" : "")} onClick={() => go("tenant")}>My wallet</button>
          <button className={"navlink" + (view === "plan" ? " on" : "")} onClick={() => go("plan")}>Plan</button>
          <button className={"navlink" + (view === "maint" ? " on" : "")} onClick={() => go("maint")}>Maintenance</button>
          <button className={"navlink" + (view === "mybookings" ? " on" : "")} onClick={() => go("mybookings")}>My bookings</button>
        </>}
        {user && user.role === "landlord" &&
          <button className={"navlink" + (view === "owner" ? " on" : "")} onClick={() => go("owner")}>My hostels</button>}
        {user && user.role === "admin" &&
          <button className={"navlink" + (view === "admin" ? " on" : "")} onClick={() => go("admin")}>Admin</button>}
        {user
          ? <button className="btn btn-ghost sm" onClick={signOut}><LogOut size={15} /> {(user.full_name || "Sign out").split(" ")[0]}</button>
          : <button className="btn btn-primary sm" onClick={() => go("auth")}>Sign in</button>}
      </nav>
    </div></header>
  );
}

/* ===================== marketplace ===================== */
function ListingCard({ l, onClick, staticCard }) {
  const img = (l.photos && l.photos[0]) || "";
  return (
    <button className={"lcard" + (staticCard ? " static" : "")} onClick={onClick} disabled={staticCard}>
      <div className="lcard-img" style={{ backgroundImage: `url(${img})` }}>
        <span className="price-tag">{ghs(l.price_per_bed)}<small> /bed/yr</small></span>
      </div>
      <div className="lcard-body">
        <div className="lcard-name disp">{l.name}</div>
        <div className="lcard-uni muted"><MapPin size={12} /> {l.university}{l.area ? ` · ${l.area}` : ""}</div>
        <div className="lcard-meta">
          <span className="chip2"><Bed size={13} /> {l.room_type}</span>
          <span className={"chip2" + ((l.available_beds || 0) <= 5 ? " low" : "")}><Users size={13} /> {l.available_beds}{staticCard ? `/${l.total_beds}` : " left"}</span>
        </div>
      </div>
    </button>
  );
}

function MarketView({ go, openListing }) {
  const [all, setAll] = useState(null);
  const [err, setErr] = useState(null);
  const [uni, setUni] = useState("");
  const [room, setRoom] = useState("");
  const [maxP, setMaxP] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    let on = true;
    Api.listings().then((d) => on && setAll(d)).catch((e) => on && setErr(e.message));
    return () => { on = false; };
  }, []);

  if (err) return <div className="wrap" style={{ paddingTop: 22 }}><div className="banner err">{err}</div></div>;
  if (!all) return <Loading label="Loading hostels…" />;

  const unis = Array.from(new Set(all.map((l) => l.university).filter(Boolean)));
  const rooms = Array.from(new Set(all.map((l) => l.room_type).filter(Boolean)));
  const filtered = all.filter((l) => {
    if (uni && l.university !== uni) return false;
    if (room && l.room_type !== room) return false;
    if (maxP && Number(l.price_per_bed) > Number(maxP)) return false;
    if (q) {
      const t = `${l.name} ${l.university} ${l.city || ""} ${l.area || ""}`.toLowerCase();
      if (!t.includes(q.toLowerCase())) return false;
    }
    return true;
  });

  return (
    <div>
      <div className="hero"><div className="wrap">
        <h1 className="h1 disp">Find your hostel near campus.</h1>
        <p className="lead muted">Browse hostels around Ghana's universities — compare rooms, prices and live availability, then book a bed. No more trekking gate to gate.</p>
        <div className="searchbar">
          <div className="sb-field"><Search size={16} /><input className="sb-input" placeholder="Search hostels or areas" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          <select className="select" value={uni} onChange={(e) => setUni(e.target.value)}><option value="">All universities</option>{unis.map((u) => <option key={u} value={u}>{u}</option>)}</select>
          <select className="select" value={room} onChange={(e) => setRoom(e.target.value)}><option value="">Any room</option>{rooms.map((r) => <option key={r} value={r}>{r}</option>)}</select>
          <input className="select" type="number" placeholder="Max GHS/bed" value={maxP} onChange={(e) => setMaxP(e.target.value)} />
        </div>
      </div></div>
      <div className="wrap">
        <div className="resultcount muted">{filtered.length} hostel{filtered.length === 1 ? "" : "s"} available</div>
        <div className="grid-cards">
          {filtered.map((l) => <ListingCard key={l.id} l={l} onClick={() => openListing(l)} />)}
        </div>
        {filtered.length === 0 && <div className="empty">No hostels match those filters yet.</div>}
      </div>
    </div>
  );
}

function ListingDetail({ listing, user, go, setPending }) {
  const [l, setL] = useState(listing && listing.amenities ? listing : null);
  const [err, setErr] = useState(null);
  const [beds, setBeds] = useState(1);
  const [moveIn, setMoveIn] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  const id = listing.id;

  useEffect(() => {
    if (l) return;
    let on = true;
    Api.listing(id).then((d) => on && setL(d)).catch((e) => on && setErr(e.message));
    return () => { on = false; };
  }, [id]);

  if (err && !l) return <div className="wrap detail"><button className="back" onClick={() => go("market")}><ArrowLeft size={15} /> Back</button><div className="banner err">{err}</div></div>;
  if (!l) return <Loading label="Loading…" />;

  const photos = l.photos && l.photos.length ? l.photos : [""];
  const submitBook = async () => {
    if (!user) { setPending(l.id); go("auth"); return; }
    setBusy(true); setErr(null);
    try {
      const b = await Api.book({ property_id: l.id, beds: Number(beds) || 1, move_in_date: moveIn || null, note: note || null });
      setDone(b);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="wrap detail">
      <button className="back" onClick={() => go("market")}><ArrowLeft size={15} /> All hostels</button>
      <div className="detail-grid">
        <div>
          <div className="gallery">
            <div className="gmain" style={{ backgroundImage: `url(${photos[0]})` }} />
            {photos.length > 1 && <div className="gthumbs">{photos.map((p, i) => <div key={i} className="gthumb" style={{ backgroundImage: `url(${p})` }} />)}</div>}
          </div>
          <h1 className="h2 disp">{l.name}</h1>
          <div className="muted"><MapPin size={13} /> {l.university}{l.area ? ` · ${l.area}` : ""}{l.city ? `, ${l.city}` : ""}</div>
          {l.description && <p className="desc">{l.description}</p>}
          <div className="amenities">{(l.amenities || []).map((a) => <span key={a} className="chip2"><CheckCircle2 size={13} /> {a}</span>)}</div>
          {l.owner && <div className="owner muted">Listed by {l.owner}</div>}
        </div>
        <div className="bookcard card shadow">
          {done ? (
            <div className="booked">
              <div className="bk-ic"><CheckCircle2 size={26} /></div>
              <div className="h3 disp">Booking requested</div>
              <p className="muted">Sent to {l.owner || "the owner"} — they'll confirm your bed. Meanwhile, save toward the advance in your wallet.</p>
              <div className="kv"><span>Hostel</span><b>{l.name}</b></div>
              <div className="kv"><span>Beds</span><b>{done.beds}</b></div>
              <div className="kv"><span>Status</span><b style={{ textTransform: "capitalize" }}>{done.status}</b></div>
              <button className="btn btn-ghost full" style={{ marginTop: 14 }} onClick={() => go(user ? "mybookings" : "market")}>{user ? "View my bookings" : "Done"}</button>
            </div>
          ) : (
            <>
              <div className="price-lg disp">{ghs(l.price_per_bed)}<small> /bed/yr</small></div>
              <div className="avail muted">{l.available_beds} of {l.total_beds} beds available · {l.room_type}</div>
              {err && <div className="banner err sm">{err}</div>}
              <label className="label">Beds</label>
              <input className="input" type="number" min="1" max={l.available_beds || 1} value={beds} onChange={(e) => setBeds(e.target.value)} />
              <label className="label">Preferred move-in</label>
              <input className="input" type="date" value={moveIn} onChange={(e) => setMoveIn(e.target.value)} />
              <label className="label">Note to owner (optional)</label>
              <textarea className="input" rows="2" value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Level 200 student, starting September" />
              <button className="btn btn-primary full" style={{ marginTop: 14 }} disabled={busy || (l.available_beds || 0) < 1} onClick={submitBook}>
                {busy ? "Requesting…" : user ? "Request booking" : "Sign in to book"}
              </button>
              {!user && <div className="hint muted">You'll create a free account first — it also sets up your rent-readiness wallet.</div>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ===================== auth ===================== */
function AuthView({ onAuthed, go }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ full_name: "", email: "", password: "", role: "tenant" });
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));

  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      const res = mode === "login"
        ? await Api.login(f.email.trim(), f.password)
        : await Api.register({ full_name: f.full_name.trim(), email: f.email.trim(), password: f.password, role: f.role });
      Token.set(res.access_token);
      onAuthed(res.user);
    } catch (e) { setErr(e.message); setBusy(false); }
  };

  return (
    <div className="authwrap"><div className="card shadow authcard">
      <div className="h2 disp" style={{ marginBottom: 2 }}>{mode === "login" ? "Welcome back" : "Create your account"}</div>
      <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>{mode === "login" ? "Sign in to book and manage your hostel." : "Book hostels and build your rent readiness."}</p>
      {err && <div className="banner err sm">{err}</div>}
      {mode === "register" && <>
        <label className="label">Full name</label>
        <input className="input" value={f.full_name} onChange={(e) => set("full_name", e.target.value)} placeholder="e.g. Adwoa Sarpong" />
        <label className="label">I am…</label>
        <div className="seg2">
          <button className={"segb" + (f.role === "tenant" ? " on" : "")} onClick={() => set("role", "tenant")}>Looking for a hostel</button>
          <button className={"segb" + (f.role === "landlord" ? " on" : "")} onClick={() => set("role", "landlord")}>A hostel owner</button>
        </div>
      </>}
      <label className="label">Email</label>
      <input className="input" type="email" value={f.email} onChange={(e) => set("email", e.target.value)} placeholder="you@email.com" />
      <label className="label">Password</label>
      <input className="input" type="password" value={f.password} onChange={(e) => set("password", e.target.value)} placeholder="••••••••" />
      <button className="btn btn-primary full" style={{ marginTop: 16 }} disabled={busy} onClick={submit}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
      <div className="switch">{mode === "login" ? "New here?" : "Already have an account?"} <button className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(null); }}>{mode === "login" ? "Create an account" : "Sign in"}</button></div>
      <div className="switch"><button className="link" onClick={() => go("market")}>← Browse hostels</button></div>
      {mode === "login" && <div className="seed-hint muted">Demo logins: <b>ama@example.com</b> / password123 (student) · <b>campus.living@example.com</b> / password123 (owner)</div>}
    </div></div>
  );
}

/* ===================== tenant dashboard ===================== */
function TenantDashboard({ user, go }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    let on = true;
    Promise.all([Api.tenant(), Api.wallet(), Api.txns(), Api.myBookings()])
      .then(([t, w, tx, bk]) => on && setD({ t, w, tx, bk }))
      .catch((e) => on && setErr(e.message));
    return () => { on = false; };
  }, []);
  if (err) return <div className="wrap" style={{ paddingTop: 22 }}><div className="banner err">{err}</div></div>;
  if (!d) return <Loading label="Loading your wallet…" />;
  const { t, w, bk, tx } = d;
  const r = w.readiness || t.readiness;
  const lvl = LEVEL[r.level] || LEVEL.yellow;

  return (
    <div className="wrap dash">
      <div className="dash-head"><div className="muted">Welcome back</div><h1 className="h1b disp">{user.full_name}</h1></div>
      <div className="dash-grid">
        <div className="card shadow pad">
          <div className="lbl">Rent Readiness Reserve</div>
          <div className="meter-shell">
            <Meter wallet={w} />
            <div className="meter-side">
              <div className="pct disp">{r.readiness_pct}%</div>
              <span className="pill" style={{ color: lvl.fg, background: lvl.bg }}>{lvl.label}</span>
              <div className="sm2 muted">{ghs(w.total)} reserved</div>
              {r.days_remaining != null && <div className="sm2 muted">Advance due in <b>{r.days_remaining} days</b></div>}
              {r.shortfall > 0 && <div className="sm2 muted">{ghs(r.shortfall)} to go</div>}
            </div>
          </div>
        </div>
        <div className="card shadow pad">
          <div className="lbl">Your five funds</div>
          {BUCKETS.map((b) => <div key={b.key} className="brow"><span><span className="sw" style={{ background: b.color }} />{b.label}</span><span className="mono">{ghs(w[b.key])}</span></div>)}
          <div className="brow total"><span>Total</span><span className="mono">{ghs(w.total)}</span></div>
        </div>
      </div>

      <div className="card shadow pad" style={{ marginTop: 16 }}>
        <div className="between"><div className="lbl">Housing trust</div><span className="pill" style={{ color: "var(--s-green-fg)", background: "var(--s-green-bg)" }}>{t.trust.band}</span></div>
        <div className="trustnum disp">{t.trust.score}<span> / 100</span></div>
        {Object.entries(t.trust.factors).map(([k, v]) => (
          <div key={k} className="factor"><span className="fl">{FACTORS[k] || k}</span><span className="fv mono">{Math.round(v)}</span><span className="bar"><span style={{ width: Math.min(100, v) + "%" }} /></span></div>
        ))}
      </div>

      <div className="card shadow pad" style={{ marginTop: 16 }}>
        <div className="lbl">My bookings</div>
        {bk.length === 0
          ? <div className="empty2 muted">No bookings yet. <button className="link" onClick={() => go("market")}>Find a hostel</button> to reserve a bed.</div>
          : bk.map((b) => <div key={b.id} className="bkrow"><div><b>{b.property_name}</b><div className="xs muted">{b.university} · {b.beds} bed(s){b.move_in_date ? ` · move-in ${b.move_in_date}` : ""}</div></div><span className="pill" style={statusStyle(b.status)}>{b.status}</span></div>)}
      </div>

      <div className="card shadow pad" style={{ marginTop: 16 }}>
        <div className="lbl">Recent contributions</div>
        {tx.length === 0
          ? <div className="empty2 muted">No transactions yet.</div>
          : tx.slice(0, 8).map((x) => {
              const b = BUCKETS.find((bb) => bb.key === x.bucket);
              const failed = x.status === "failed";
              return <div key={x.id} className="bkrow"><div className="row" style={{ gap: 9 }}><span className="sw" style={{ background: b ? b.color : "#ccc" }} /><div><b style={{ fontSize: 13.5 }}>{b ? b.label : x.bucket}</b><div className="xs muted">{x.method || ""}</div></div></div><div className="row gap"><span className="mono" style={{ fontWeight: 600 }}>{ghs(x.amount)}</span><span className="pill" style={statusStyle(failed ? "cancelled" : "confirmed")}>{failed ? "Failed" : "Success"}</span></div></div>;
            })}
      </div>
    </div>
  );
}

function MyBookings({ go }) {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { let on = true; Api.myBookings().then((d) => on && setRows(d)).catch((e) => on && setErr(e.message)); return () => { on = false; }; }, []);
  if (err) return <div className="wrap" style={{ paddingTop: 22 }}><div className="banner err">{err}</div></div>;
  if (!rows) return <Loading label="Loading your bookings…" />;
  return (
    <div className="wrap dash">
      <div className="dash-head"><h1 className="h1b disp">My bookings</h1></div>
      {rows.length === 0
        ? <div className="card shadow pad center muted">No bookings yet. <button className="link" onClick={() => go("market")}>Find a hostel</button>.</div>
        : <div className="card shadow pad">{rows.map((b) => <div key={b.id} className="bkrow"><div><b>{b.property_name}</b><div className="xs muted">{b.university} · {b.beds} bed(s){b.move_in_date ? ` · move-in ${b.move_in_date}` : ""}</div></div><span className="pill" style={statusStyle(b.status)}>{b.status}</span></div>)}</div>}
    </div>
  );
}

/* ===================== owner ===================== */
function OwnerListings() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { let on = true; Api.myListings().then((d) => on && setRows(d)).catch((e) => on && setErr(e.message)); return () => { on = false; }; }, []);
  if (err) return <div className="banner err">{err}</div>;
  if (!rows) return <Loading label="Loading…" />;
  if (rows.length === 0) return <div className="card shadow pad center muted">You haven't listed any hostels yet. Use “List a hostel”.</div>;
  return <div className="grid-cards">{rows.map((l) => <ListingCard key={l.id} l={l} staticCard onClick={() => {}} />)}</div>;
}

function OwnerNew({ onCreated }) {
  const [f, setF] = useState({ name: "", university: UNIS[0], city: "Accra", area: "", room_type: "4-in-1", price_per_bed: "", total_beds: "", available_beds: "", amenities: "WiFi, 24/7 Water, Security", photos: "", description: "" });
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState(false);
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));

  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      const body = {
        name: f.name.trim(), university: f.university, city: f.city, area: f.area, room_type: f.room_type,
        price_per_bed: Number(f.price_per_bed) || 0, total_beds: Number(f.total_beds) || 1,
        amenities: f.amenities.split(",").map((s) => s.trim()).filter(Boolean),
        photos: f.photos.split(/[\n,]/).map((s) => s.trim()).filter(Boolean),
        description: f.description.trim(),
      };
      if (f.available_beds) body.available_beds = Number(f.available_beds);
      await Api.createListing(body);
      setOk(true);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  if (ok) return <div className="card shadow pad center"><div className="bk-ic"><CheckCircle2 size={26} /></div><div className="h3 disp">Hostel listed</div><p className="muted">It's now searchable by students.</p><button className="btn btn-primary" onClick={onCreated}>View my hostels</button></div>;

  return (
    <div className="card shadow pad">
      {err && <div className="banner err sm">{err}</div>}
      <div className="formgrid">
        <Field2 label="Hostel name" full><input className="input" value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Pearl Court Hostel" /></Field2>
        <Field2 label="University"><select className="input" value={f.university} onChange={(e) => set("university", e.target.value)}>{UNIS.map((u) => <option key={u}>{u}</option>)}</select></Field2>
        <Field2 label="City"><input className="input" value={f.city} onChange={(e) => set("city", e.target.value)} /></Field2>
        <Field2 label="Area / landmark"><input className="input" value={f.area} onChange={(e) => set("area", e.target.value)} placeholder="e.g. Ayeduase" /></Field2>
        <Field2 label="Room type"><select className="input" value={f.room_type} onChange={(e) => set("room_type", e.target.value)}>{ROOMS.map((r) => <option key={r}>{r}</option>)}</select></Field2>
        <Field2 label="Price (GHS / bed / yr)"><input className="input" type="number" value={f.price_per_bed} onChange={(e) => set("price_per_bed", e.target.value)} /></Field2>
        <Field2 label="Total beds"><input className="input" type="number" value={f.total_beds} onChange={(e) => set("total_beds", e.target.value)} /></Field2>
        <Field2 label="Available beds"><input className="input" type="number" value={f.available_beds} onChange={(e) => set("available_beds", e.target.value)} placeholder="defaults to total" /></Field2>
        <Field2 label="Amenities (comma-separated)" full><input className="input" value={f.amenities} onChange={(e) => set("amenities", e.target.value)} /></Field2>
        <Field2 label="Photo URLs (one per line)" full><textarea className="input" rows="3" value={f.photos} onChange={(e) => set("photos", e.target.value)} placeholder="https://…/photo1.jpg" /></Field2>
        <Field2 label="Description" full><textarea className="input" rows="2" value={f.description} onChange={(e) => set("description", e.target.value)} /></Field2>
      </div>
      <button className="btn btn-primary full" style={{ marginTop: 14 }} disabled={busy} onClick={submit}>{busy ? "Listing…" : "List hostel"}</button>
      <div className="hint muted">Paste image links for now — photo upload is the next step.</div>
    </div>
  );
}

function OwnerBookings() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(0);
  const load = useCallback(() => { Api.incoming().then(setRows).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { load(); }, [load]);
  if (err) return <div className="banner err">{err}</div>;
  if (!rows) return <Loading label="Loading bookings…" />;
  if (rows.length === 0) return <div className="card shadow pad center muted">No booking requests yet.</div>;
  const act = async (id, status) => { setBusy(id); setErr(null); try { await Api.setBooking(id, status); load(); } catch (e) { setErr(e.message); } finally { setBusy(0); } };
  return (
    <div className="card shadow pad">
      {rows.map((b) => (
        <div key={b.id} className="bkrow">
          <div><b>{b.property_name}</b><div className="xs muted">{b.beds} bed(s){b.move_in_date ? ` · move-in ${b.move_in_date}` : ""} · requested {fmtDate(b.created_at)}</div></div>
          <div className="row gap">
            <span className="pill" style={statusStyle(b.status)}>{b.status}</span>
            {b.status === "pending" && <>
              <button className="btn btn-primary xs" disabled={busy === b.id} onClick={() => act(b.id, "confirmed")}>Confirm</button>
              <button className="btn btn-ghost xs" disabled={busy === b.id} onClick={() => act(b.id, "cancelled")}>Decline</button>
            </>}
          </div>
        </div>
      ))}
    </div>
  );
}

function OwnerView({ user }) {
  const [tab, setTab] = useState("listings");
  return (
    <div className="wrap dash">
      <div className="dash-head"><div className="muted">Owner dashboard</div><h1 className="h1b disp">{user.full_name}</h1></div>
      <div className="tabs">
        <button className={"tab" + (tab === "listings" ? " on" : "")} onClick={() => setTab("listings")}>My hostels</button>
        <button className={"tab" + (tab === "new" ? " on" : "")} onClick={() => setTab("new")}>List a hostel</button>
        <button className={"tab" + (tab === "bookings" ? " on" : "")} onClick={() => setTab("bookings")}>Bookings</button>
        <button className={"tab" + (tab === "properties" ? " on" : "")} onClick={() => setTab("properties")}>Properties</button>
        <button className={"tab" + (tab === "maint" ? " on" : "")} onClick={() => setTab("maint")}>Maintenance</button>
        <button className={"tab" + (tab === "leases" ? " on" : "")} onClick={() => setTab("leases")}>Leases</button>
      </div>
      {tab === "listings" && <OwnerListings />}
      {tab === "new" && <OwnerNew onCreated={() => setTab("listings")} />}
      {tab === "bookings" && <OwnerBookings />}
      {tab === "properties" && <OwnerProperties />}
      {tab === "maint" && <OwnerMaintenance />}
      {tab === "leases" && <OwnerLeases />}
    </div>
  );
}

/* ===================== landlord: properties / maintenance / leases ===================== */
function OwnerProperties() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState(null);
  const [show, setShow] = useState(false);
  const [f, setF] = useState({ name: "", address: "", city: "Accra", property_type: "Apartment", monthly_rent: "", advance_rent: "" });
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { Api.properties().then(setRows).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { load(); }, [load]);
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      await Api.createProperty({ name: f.name.trim(), address: f.address, city: f.city, property_type: f.property_type, monthly_rent: Number(f.monthly_rent) || 0, advance_rent: Number(f.advance_rent) || 0 });
      setShow(false); setF({ name: "", address: "", city: "Accra", property_type: "Apartment", monthly_rent: "", advance_rent: "" }); load();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  if (err) return <div className="banner err">{err}</div>;
  if (!rows) return <Loading label="Loading…" />;
  return (
    <div>
      <div className="row between" style={{ marginBottom: 12 }}><div className="xs muted">{rows.length} propert{rows.length === 1 ? "y" : "ies"}</div><button className="btn btn-ghost xs" onClick={() => setShow(!show)}>{show ? "Cancel" : "+ Add property"}</button></div>
      {show && <div className="card shadow pad" style={{ marginBottom: 16 }}>
        <div className="formgrid">
          <Field2 label="Name" full><input className="input" value={f.name} onChange={(e) => set("name", e.target.value)} /></Field2>
          <Field2 label="Type"><select className="input" value={f.property_type} onChange={(e) => set("property_type", e.target.value)}>{["Apartment", "Townhouse", "Studio", "Single room", "Hostel"].map((t) => <option key={t}>{t}</option>)}</select></Field2>
          <Field2 label="City"><input className="input" value={f.city} onChange={(e) => set("city", e.target.value)} /></Field2>
          <Field2 label="Address" full><input className="input" value={f.address} onChange={(e) => set("address", e.target.value)} /></Field2>
          <Field2 label="Monthly rent (GHS)"><input className="input" type="number" value={f.monthly_rent} onChange={(e) => set("monthly_rent", e.target.value)} /></Field2>
          <Field2 label="Advance (GHS)"><input className="input" type="number" value={f.advance_rent} onChange={(e) => set("advance_rent", e.target.value)} /></Field2>
        </div>
        <button className="btn btn-primary full" style={{ marginTop: 12 }} disabled={busy || !f.name} onClick={submit}>{busy ? "Adding…" : "Add property"}</button>
      </div>}
      {rows.length === 0 ? <div className="card shadow pad center muted">No properties yet.</div> :
        <div className="card shadow pad">{rows.map((p) => <div key={p.id} className="bkrow"><div><b>{p.name}</b><div className="xs muted">{p.property_type}{p.city ? ` · ${p.city}` : ""} · {(p.occupancy_status || "").replace(/_/g, " ")}</div></div><span className="mono" style={{ fontWeight: 600 }}>{p.advance_rent ? ghs(p.advance_rent) : p.monthly_rent ? ghs(p.monthly_rent) : "—"}</span></div>)}</div>}
    </div>
  );
}

function OwnerMaintenance() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(0);
  const STATUSES = ["landlord_notified", "contractor_assigned", "in_progress", "completed", "disputed"];
  const load = useCallback(() => { Api.maintenance().then(setRows).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { load(); }, [load]);
  if (err) return <div className="banner err">{err}</div>;
  if (!rows) return <Loading label="Loading…" />;
  if (rows.length === 0) return <div className="card shadow pad center muted">No maintenance requests.</div>;
  const setS = async (id, status) => { setBusy(id); setErr(null); try { await Api.setMaintenance(id, status); load(); } catch (e) { setErr(e.message); } finally { setBusy(0); } };
  return <div className="card shadow pad">{rows.map((m) => <div key={m.id} className="bkrow"><div><b>{m.issue_type || "Issue"}</b><div className="xs muted">{m.description}</div></div><div className="row gap"><span className="pill" style={urgencyStyle(m.urgency)}>{m.urgency}</span><select className="ministatus" value={m.status} disabled={busy === m.id} onChange={(e) => setS(m.id, e.target.value)}>{STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}</select></div></div>)}</div>;
}

function OwnerLeases() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { Promise.all([Api.landlordLeases(), Api.properties()]).then(([ls, ps]) => setData({ ls, ps })).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="banner err">{err}</div>;
  if (!data) return <Loading label="Loading…" />;
  const { ls, ps } = data;
  const pname = (id) => { const p = ps.find((x) => x.id === id); return p ? p.name : `Property #${id}`; };
  const expected = ls.reduce((s, l) => s + (l.rent_amount || 0), 0);
  if (ls.length === 0) return <div className="card shadow pad center muted">No leases yet.</div>;
  return (
    <div>
      <div className="card shadow statc" style={{ marginBottom: 14, maxWidth: 240 }}><div className="xs muted">Expected rent</div><div className="statv disp">{ghs(expected)}</div></div>
      <div className="card shadow pad">{ls.map((l) => <div key={l.id} className="bkrow"><div><b>{pname(l.property_id)}</b><div className="xs muted">{(l.payment_cycle || "").replace(/_/g, " ")}{l.start_date ? ` · ${l.start_date} → ${l.end_date || ""}` : ""}</div></div><div className="row gap"><span className="mono" style={{ fontWeight: 600 }}>{ghs(l.rent_amount)}</span><span className="pill" style={statusStyle(l.status === "active" ? "confirmed" : "pending")}>{l.status}</span></div></div>)}</div>
    </div>
  );
}

/* ===================== tenant: contribution plan ===================== */
function TenantPlan() {
  const [amount, setAmount] = useState(200);
  const [freq, setFreq] = useState("weekly");
  const [proj, setProj] = useState(null);
  const [err, setErr] = useState(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Api.plan().then((p) => { if (p) { setAmount(p.amount); setFreq(p.frequency); } }).catch(() => {}).finally(() => setLoaded(true));
  }, []);

  useEffect(() => {
    if (!loaded) return;
    const id = setTimeout(() => { Api.projection(amount || 0, freq).then(setProj).catch((e) => setErr(e.message)); }, 350);
    return () => clearTimeout(id);
  }, [amount, freq, loaded]);

  const save = async () => {
    setBusy(true); setErr(null);
    try { await Api.savePlan({ amount: Number(amount) || 0, frequency: freq }); setSaved(true); setTimeout(() => setSaved(false), 2500); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="wrap dash">
      <div className="dash-head"><div className="muted">Plan your savings</div><h1 className="h1b disp">Contribution plan</h1></div>
      {err && <div className="banner err">{err}</div>}
      <div className="dash-grid">
        <div className="card shadow pad">
          <label className="label">I'll contribute (GHS)</label>
          <input className="input" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
          <label className="label">How often</label>
          <select className="input" value={freq} onChange={(e) => setFreq(e.target.value)}>
            {["daily", "weekly", "biweekly", "monthly", "seasonal"].map((x) => <option key={x} value={x}>{x[0].toUpperCase() + x.slice(1)}</option>)}
          </select>
          <button className="btn btn-primary full" style={{ marginTop: 16 }} disabled={busy} onClick={save}>{busy ? "Saving…" : saved ? "Saved ✓" : "Save plan"}</button>
        </div>
        <div className="card shadow pad">
          <div className="lbl">Projected at your due date</div>
          {!proj ? <div className="empty2 muted">Adjusting…</div> : <>
            <div className="pct disp" style={{ fontSize: 40 }}>{proj.projected_readiness_pct}%</div>
            <div className="sm2 muted">projected readiness in {proj.days_remaining} days</div>
            <div className="brow" style={{ marginTop: 12 }}><span>Projected balance</span><span className="mono">{ghs(proj.projected_balance)}</span></div>
            <div className="brow"><span>Shortfall</span><span className="mono">{ghs(proj.shortfall)}</span></div>
            {proj.recommended_contribution > 0 && <div className="brow"><span>To fully cover it</span><span className="mono">{ghs(proj.recommended_contribution)} / {freq}</span></div>}
          </>}
        </div>
      </div>
    </div>
  );
}

/* ===================== tenant: maintenance ===================== */
function TenantMaintenance() {
  const [lease, setLease] = useState(undefined);
  const [list, setList] = useState(null);
  const [err, setErr] = useState(null);
  const [f, setF] = useState({ issue_type: "", description: "" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => { Api.maintenance().then(setList).catch((e) => setErr(e.message)); }, []);
  useEffect(() => {
    Api.myLease().then((rows) => setLease(rows && rows.length ? rows[0] : null)).catch(() => setLease(null));
    load();
  }, [load]);

  const submit = async () => {
    if (!lease) return;
    setBusy(true); setErr(null);
    try { await Api.createMaintenance({ property_id: lease.property_id, issue_type: f.issue_type, description: f.description }); setF({ issue_type: "", description: "" }); load(); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="wrap dash">
      <div className="dash-head"><div className="muted">Repairs & issues</div><h1 className="h1b disp">Maintenance</h1></div>
      {err && <div className="banner err">{err}</div>}
      <div className="dash-grid">
        <div className="card shadow pad">
          <div className="lbl">Report an issue</div>
          {lease === null ? <div className="empty2 muted">No active lease on file to report against.</div> : <>
            <label className="label">Issue type</label>
            <input className="input" value={f.issue_type} onChange={(e) => setF({ ...f, issue_type: e.target.value })} placeholder="e.g. Plumbing, Electrical" />
            <label className="label">What's wrong?</label>
            <textarea className="input" rows="3" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} placeholder="Describe the problem" />
            <button className="btn btn-primary full" style={{ marginTop: 14 }} disabled={busy || !f.description} onClick={submit}>{busy ? "Submitting…" : "Submit request"}</button>
            <div className="hint muted">Urgency is auto-classified from your description.</div>
          </>}
        </div>
        <div className="card shadow pad">
          <div className="lbl">Your requests</div>
          {!list ? <Loading label="Loading…" /> : list.length === 0 ? <div className="empty2 muted">No requests yet.</div> :
            list.map((m) => <div key={m.id} className="bkrow"><div><b>{m.issue_type || "Issue"}</b><div className="xs muted">{m.description}</div></div><div className="row gap"><span className="pill" style={urgencyStyle(m.urgency)}>{m.urgency}</span><span className="pill" style={{ background: "#F4F1E8", color: "var(--muted)" }}>{(m.status || "").replace(/_/g, " ")}</span></div></div>)}
        </div>
      </div>
    </div>
  );
}

/* ===================== admin console ===================== */
function AdminOverviewTab() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { Api.adminOverview().then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="banner err">{err}</div>;
  if (!d) return <Loading label="Loading…" />;
  const cards = [
    ["Users", d.users], ["Tenants", d.tenants], ["Landlords", d.landlords], ["Active leases", d.active_leases],
    ["Properties", d.properties], ["Reserves held", ghs(d.wallet_reserves_total)], ["Pending approvals", d.pending_approvals], ["At-risk tenants", d.at_risk_tenants],
  ];
  return <div className="statgrid">{cards.map(([k, v]) => <div key={k} className="card shadow statc"><div className="xs muted">{k}</div><div className="statv disp">{v}</div></div>)}</div>;
}
function AdminRiskTab() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { Api.adminRisk().then(setRows).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="banner err">{err}</div>;
  if (!rows) return <Loading label="Loading…" />;
  if (rows.length === 0) return <div className="card shadow pad center muted">No tenants on the watchlist.</div>;
  return <div className="card shadow pad">{rows.map((r) => { const lv = LEVEL[r.level] || LEVEL.yellow; return <div key={r.tenant_id} className="bkrow"><div><b>{r.name}</b><div className="xs muted">readiness {r.readiness_pct}% · trust {r.trust_score}</div></div><span className="pill" style={{ color: lv.fg, background: lv.bg }}>{r.level}</span></div>; })}</div>;
}
function AdminApprovalsTab() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(0);
  const load = useCallback(() => { Api.adminApprovals().then(setRows).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { load(); }, [load]);
  if (err) return <div className="banner err">{err}</div>;
  if (!rows) return <Loading label="Loading…" />;
  if (rows.length === 0) return <div className="card shadow pad center muted">Nothing pending approval.</div>;
  const approve = async (id) => { setBusy(id); setErr(null); try { await Api.approveUser(id); load(); } catch (e) { setErr(e.message); } finally { setBusy(0); } };
  return <div className="card shadow pad">{rows.map((u) => <div key={u.id} className="bkrow"><div><b>{u.full_name}</b><div className="xs muted">{u.email} · {u.role}</div></div><button className="btn btn-primary xs" disabled={busy === u.id} onClick={() => approve(u.id)}>Approve</button></div>)}</div>;
}
function AdminView() {
  const [tab, setTab] = useState("overview");
  return (
    <div className="wrap dash">
      <div className="dash-head"><div className="muted">Platform admin</div><h1 className="h1b disp">Sahara Square</h1></div>
      <div className="tabs">
        <button className={"tab" + (tab === "overview" ? " on" : "")} onClick={() => setTab("overview")}>Overview</button>
        <button className={"tab" + (tab === "risk" ? " on" : "")} onClick={() => setTab("risk")}>Risk</button>
        <button className={"tab" + (tab === "approvals" ? " on" : "")} onClick={() => setTab("approvals")}>Approvals</button>
      </div>
      {tab === "overview" && <AdminOverviewTab />}
      {tab === "risk" && <AdminRiskTab />}
      {tab === "approvals" && <AdminApprovalsTab />}
    </div>
  );
}

/* ===================== root ===================== */
function changeApi() {
  const v = prompt("Backend API base URL", apiBase());
  if (v) { sessionStorage.setItem("mrsw_api", v.replace(/\/$/, "")); location.reload(); }
}

export default function App() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState("market");
  const [selected, setSelected] = useState(null);
  const [pending, setPending] = useState(null);
  const [boot, setBoot] = useState(true);

  useEffect(() => {
    if (Token.get()) Api.me().then(setUser).catch(() => Token.set(null)).finally(() => setBoot(false));
    else setBoot(false);
  }, []);

  const go = (v) => { setView(v); window.scrollTo(0, 0); };
  const openListing = (l) => { setSelected(l); go("listing"); };
  const onAuthed = (u) => {
    setUser(u);
    if (pending) {
      const id = pending; setPending(null);
      Api.listing(id).then((l) => { setSelected(l); go("listing"); }).catch(() => go(u.role === "landlord" ? "owner" : "market"));
    } else go(u.role === "landlord" ? "owner" : "tenant");
  };
  const signOut = () => { Token.set(null); setUser(null); go("market"); };

  return (
    <div className="app">
      <style>{CSS}</style>
      <Header user={user} view={view} go={go} signOut={signOut} />
      <main>
        {boot ? <Loading label="Loading…" />
          : view === "listing" && selected ? <ListingDetail listing={selected} user={user} go={go} setPending={setPending} />
          : view === "auth" ? <AuthView onAuthed={onAuthed} go={go} />
          : view === "tenant" && user ? <TenantDashboard user={user} go={go} />
          : view === "plan" && user ? <TenantPlan />
          : view === "maint" && user ? <TenantMaintenance />
          : view === "mybookings" && user ? <MyBookings go={go} />
          : view === "owner" && user ? <OwnerView user={user} />
          : view === "admin" && user ? <AdminView />
          : <MarketView go={go} openListing={openListing} />}
      </main>
      <footer className="foot"><span className="muted">MRSW RentConnect · <button className="link" onClick={changeApi}>API: {apiBase().replace(/^https?:\/\//, "")}</button></span></footer>
    </div>
  );
}

/* ===================== styles ===================== */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');
:root{--ink:#1B1410;--muted:#6F6557;--line:#E7E1D3;--sand:#FAF7EF;--surface:#fff;--green:#0F4D38;--green2:#1F7A5C;--gold:#B68A2E;--s-green-fg:#15604A;--s-green-bg:#E7F0EA;--s-amber-fg:#8A6B12;--s-amber-bg:#F6EED6;--s-orange-fg:#A6502A;--s-orange-bg:#F5E5D8;--s-red-fg:#9E3636;--s-red-bg:#F5E0E0;}
*{box-sizing:border-box}
.app{min-height:100vh;background:var(--sand);color:var(--ink);font-family:'Plus Jakarta Sans',system-ui,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}
.disp{font-family:'Bricolage Grotesque',serif}
.mono{font-family:'JetBrains Mono',monospace;font-variant-numeric:tabular-nums}
.muted{color:var(--muted)}
.gold{color:var(--gold)}
.row{display:flex;align-items:center}
.row.gap{gap:8px}
.between{display:flex;align-items:center;justify-content:space-between}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
button{font:inherit;cursor:pointer}
.link{background:none;border:none;color:var(--green);font-weight:600;padding:0;text-decoration:underline}
.bar{position:sticky;top:0;z-index:20;background:rgba(250,247,239,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.bar-in{max-width:1080px;margin:0 auto;padding:11px 20px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;background:none;border:none}
.logo{width:32px;height:32px;border-radius:9px;background:var(--green);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.logo span{color:#fff;font-weight:800;font-size:15px}
.brandtext{text-align:left}
.bn{font-weight:800;font-size:15px;line-height:1}
.bs{font-size:10.5px;color:var(--muted);font-weight:600;letter-spacing:.03em}
.nav{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.navlink{background:none;border:none;color:var(--ink);font-weight:600;font-size:13.5px;padding:7px 10px;border-radius:8px}
.navlink:hover{background:#FBF9F3}
.navlink.on{color:var(--green)}
.btn{font-weight:700;border-radius:11px;padding:11px 16px;border:1px solid transparent;display:inline-flex;align-items:center;gap:7px;transition:.15s;justify-content:center}
.btn.sm{padding:8px 12px;font-size:13.5px}
.btn.xs{padding:6px 11px;font-size:12.5px;border-radius:9px}
.btn.full{width:100%}
.btn-primary{background:var(--green);color:#fff}
.btn-primary:hover{background:#0c3f2e}
.btn-primary:disabled{opacity:.5;cursor:not-allowed}
.btn-ghost{background:#fff;color:var(--ink);border-color:var(--line)}
.btn-ghost:hover{background:#FBF9F3}
.hero{background:linear-gradient(160deg,#11422F 0%,#0F4D38 60%,#15604A 100%);color:#fff;padding:36px 0 64px}
.hero .muted{color:rgba(255,255,255,.82)}
.h1{font-size:34px;font-weight:800;letter-spacing:-.02em;margin:0;color:#fff}
.h1b{font-size:28px;font-weight:800;margin:2px 0 0}
.h2{font-size:24px;font-weight:800;margin:6px 0 2px}
.h3{font-size:18px;font-weight:800;margin:6px 0}
.lead{font-size:15px;max-width:580px;margin:10px 0 0}
.searchbar{margin-top:20px;background:#fff;border-radius:14px;padding:8px;display:flex;gap:8px;flex-wrap:wrap;box-shadow:0 18px 40px -24px rgba(0,0,0,.5)}
.sb-field{flex:1;min-width:180px;display:flex;align-items:center;gap:8px;padding:0 12px;background:#FBF9F3;border-radius:10px;color:var(--muted)}
.sb-input{flex:1;border:none;background:none;font:inherit;padding:11px 0;outline:none;color:var(--ink)}
.select{border:1px solid var(--line);background:#fff;border-radius:10px;padding:11px 12px;font:inherit;color:var(--ink);min-width:130px}
.resultcount{margin:18px 0 12px;font-size:13px;font-weight:600}
.grid-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;padding-bottom:48px}
.lcard{text-align:left;background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;padding:0;transition:.15s;display:flex;flex-direction:column}
.lcard:hover{transform:translateY(-2px);box-shadow:0 18px 36px -24px rgba(27,20,16,.45)}
.lcard.static{cursor:default}
.lcard.static:hover{transform:none;box-shadow:none}
.lcard-img{height:150px;background-size:cover;background-position:center;background-color:#E7E1D3;position:relative}
.price-tag{position:absolute;left:10px;bottom:10px;background:rgba(15,77,56,.94);color:#fff;font-weight:700;font-size:13px;padding:5px 9px;border-radius:8px}
.price-tag small{font-weight:500;opacity:.85;font-size:10.5px}
.lcard-body{padding:13px 14px 15px}
.lcard-name{font-weight:800;font-size:15.5px;line-height:1.2}
.lcard-uni{font-size:12px;margin-top:4px;display:flex;align-items:center;gap:4px}
.lcard-meta{display:flex;gap:7px;margin-top:11px;flex-wrap:wrap}
.chip2{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;color:var(--muted);background:#F4F1E8;border-radius:7px;padding:4px 8px}
.chip2.low{color:var(--s-orange-fg);background:var(--s-orange-bg)}
.empty{padding:30px;text-align:center;color:var(--muted)}
.center{text-align:center}
.detail{padding-top:20px;padding-bottom:48px}
.back{background:none;border:none;color:var(--muted);font-weight:600;display:inline-flex;align-items:center;gap:6px;margin-bottom:14px}
.detail-grid{display:grid;grid-template-columns:1fr;gap:22px}
.gallery{margin-bottom:16px}
.gmain{height:300px;border-radius:16px;background-size:cover;background-position:center;background-color:#E7E1D3}
.gthumbs{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.gthumb{width:80px;height:56px;border-radius:9px;background-size:cover;background-position:center;background-color:#E7E1D3}
.desc{font-size:14.5px;line-height:1.6;color:#473f34;margin:12px 0}
.amenities{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.owner{font-size:12.5px;margin-top:14px}
.bookcard{padding:20px;align-self:start;position:sticky;top:80px}
.price-lg{font-size:28px;font-weight:800}
.price-lg small{font-size:13px;font-weight:500;color:var(--muted)}
.avail{font-size:12.5px;margin:2px 0 14px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px}
.shadow{box-shadow:0 18px 40px -28px rgba(27,20,16,.45)}
.pad{padding:20px}
.label{display:block;font-size:12.5px;font-weight:600;color:var(--muted);margin:12px 0 6px}
.input{width:100%;font:inherit;padding:11px 13px;border:1px solid var(--line);border-radius:11px;background:#fff;color:var(--ink)}
.input:focus{outline:none;border-color:var(--green2);box-shadow:0 0 0 3px rgba(31,122,92,.12)}
textarea.input{resize:vertical}
.hint{font-size:12px;margin-top:8px}
.booked{text-align:center}
.bk-ic{width:54px;height:54px;border-radius:999px;background:var(--s-green-bg);color:var(--s-green-fg);display:flex;align-items:center;justify-content:center;margin:0 auto 10px}
.kv{display:flex;justify-content:space-between;font-size:13.5px;padding:7px 0;border-top:1px solid var(--line)}
.kv span{color:var(--muted)}
.banner{border-radius:11px;padding:11px 13px;font-size:13.5px;margin-bottom:12px}
.banner.err{background:var(--s-red-bg);color:var(--s-red-fg)}
.banner.sm{font-size:12.5px;padding:9px 11px}
.authwrap{display:flex;justify-content:center;padding:40px 20px}
.authcard{width:100%;max-width:400px;padding:26px}
.seg2{display:flex;gap:8px;margin-bottom:2px}
.segb{flex:1;background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px;font-weight:600;font-size:12.5px;color:var(--ink)}
.segb.on{border-color:var(--green);background:var(--s-green-bg);color:var(--s-green-fg)}
.switch{margin-top:12px;font-size:13px;text-align:center;color:var(--muted)}
.seed-hint{margin-top:14px;font-size:11.5px;background:#F4F1E8;border:1px solid var(--line);border-radius:9px;padding:9px 11px}
.dash{padding-top:22px;padding-bottom:48px}
.dash-head{margin-bottom:16px}
.dash-grid{display:grid;grid-template-columns:1fr;gap:16px}
.lbl{font-size:12.5px;font-weight:600;color:var(--muted);margin-bottom:14px}
.meter-shell{display:flex;gap:18px}
.meter{position:relative;width:100px;height:260px;flex-shrink:0}
.vessel{position:absolute;inset:0;border:2px solid var(--line);border-radius:18px;background:#fff;overflow:hidden}
.fill{position:absolute;inset:0;display:flex;flex-direction:column-reverse}
.seg{width:100%;transition:height .8s cubic-bezier(.22,1,.36,1)}
.target{position:absolute;left:-7px;right:-7px;top:0;border-top:2px dashed var(--gold)}
.target b{position:absolute;right:0;top:-17px;font-size:10px;font-weight:700;color:var(--gold);white-space:nowrap}
.meter-side{display:flex;flex-direction:column;justify-content:center;gap:3px}
.pct{font-size:44px;font-weight:800;line-height:1;color:var(--green)}
.sm2{font-size:12.5px}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:700;padding:4px 10px;border-radius:999px;align-self:flex-start;text-transform:capitalize}
.brow{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-top:1px solid var(--line);font-size:13.5px;font-weight:600}
.brow:first-of-type{border-top:none}
.brow.total{border-top:2px solid var(--line);font-weight:800}
.sw{width:11px;height:11px;border-radius:3px;display:inline-block;margin-right:9px;vertical-align:middle}
.trustnum{font-size:30px;font-weight:800;line-height:1.1;margin:2px 0 6px}
.trustnum span{font-size:15px;color:var(--muted)}
.factor{display:grid;grid-template-columns:1fr auto;gap:3px 12px;align-items:center;padding:6px 0}
.fl{font-size:12.5px}
.fv{font-size:12px;color:var(--muted)}
.bar{grid-column:1/-1;height:7px;border-radius:999px;background:#EFEADE;overflow:hidden}
.bar>span{display:block;height:100%;background:var(--green2);border-radius:999px}
.bkrow{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 0;border-top:1px solid var(--line)}
.bkrow:first-child{border-top:none}
.xs{font-size:12px}
.empty2{padding:8px 0;font-size:13.5px}
.tabs{display:flex;gap:6px;margin-bottom:16px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.tab{background:none;border:none;padding:10px 14px;font-weight:600;font-size:14px;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px}
.tab.on{color:var(--green);border-bottom-color:var(--green)}
.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}
.f2.full{grid-column:1/-1}
.loading{display:flex;align-items:center;justify-content:center;gap:10px;min-height:40vh;color:var(--muted);font-size:14px}
.spinner{width:18px;height:18px;border:2px solid var(--line);border-top-color:var(--green);border-radius:999px;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.foot{border-top:1px solid var(--line);padding:18px 20px;text-align:center;font-size:12px}
.statgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px}
.statc{padding:16px 18px}
.statv{font-size:26px;font-weight:800;margin-top:4px}
.ministatus{font:inherit;font-size:12px;padding:5px 8px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}
@media(min-width:820px){.detail-grid{grid-template-columns:1.6fr 1fr}.dash-grid{grid-template-columns:240px 1fr}}
@media(max-width:560px){.h1{font-size:26px}.gmain{height:210px}.formgrid{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
`;
