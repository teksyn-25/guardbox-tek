import React, { useState, useMemo, useEffect, useCallback } from "react";

/*  GuardBox — Dashboard
    Auth: Telegram OAuth redirect → POST /auth → Bearer token in localStorage.
    Data: GET /files?state=pending + GET /files?state=saved on each load.
    No SEED data. No filename stored. No size metadata.
    Viewer shows a screenshot via signed URL — no file is sent to device.    */

const FONT_DISPLAY = '"Space Grotesk", "Segoe UI", system-ui, sans-serif';
const FONT_BODY    = '"Inter", system-ui, sans-serif';
const FONT_MONO    = '"JetBrains Mono", "SF Mono", ui-monospace, monospace';

const C = {
  bg:        "#06120f",
  bgGrad:    "radial-gradient(ellipse at 50% 0%, #0a2421 0%, #06120f 55%)",
  panel:     "rgba(255,255,255,0.04)",
  panelHi:   "rgba(255,255,255,0.07)",
  line:      "rgba(255,255,255,0.08)",
  lineHi:    "rgba(52,224,161,0.35)",
  ink:       "#eaf2f0",
  inkDim:    "#9eb3b0",
  inkFaint:  "#5d7672",
  safe:      "#34e0a1",
  safeDim:   "rgba(52,224,161,0.12)",
  amber:     "#e8b450",
  danger:    "#ff6b6b",
  dangerDim: "rgba(255,107,107,0.12)",
};

const API = (import.meta.env.VITE_GUARDBOX_API_URL ?? "").replace(/\/$/, "");
const BOT_ID = import.meta.env.VITE_TELEGRAM_BOT_ID ?? "";

const SOURCE_LABEL = {
  telegram_bot: "Telegram",
  share_sheet:  "WhatsApp",
};

// Deterministic display hue from file_id — no random state, no stored color
function fileHue(file_id) {
  let h = 0;
  for (let i = 0; i < file_id.length; i++) h = (h * 31 + file_id.charCodeAt(i)) >>> 0;
  return h % 360;
}

function apiFetch(path, token, opts = {}) {
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { Authorization: `Bearer ${token}`, ...(opts.headers ?? {}) },
  });
}

// ── Telegram OAuth ────────────────────────────────────────────────────────────

function telegramLoginUrl() {
  const origin = window.location.origin;
  return `https://oauth.telegram.org/auth?bot_id=${BOT_ID}&origin=${encodeURIComponent(origin)}&return_to=${encodeURIComponent(window.location.href)}`;
}

async function handleTelegramCallback(setToken, setError) {
  const params = new URLSearchParams(window.location.search);
  const raw = params.get("tgAuthResult");
  if (!raw) return false;

  // Clean the URL so the token doesn't linger in history
  window.history.replaceState({}, "", window.location.pathname);

  let payload;
  try {
    payload = JSON.parse(atob(raw.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    setError("Invalid Telegram auth response.");
    return true;
  }

  const res = await fetch(`${API}/auth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    setError("Telegram login failed. Please try again.");
    return true;
  }

  const { token } = await res.json();
  localStorage.setItem("gb_token", token);
  setToken(token);
  return true;
}

// ── Main app ──────────────────────────────────────────────────────────────────

export default function GuardBoxDashboard() {
  const [token, setToken]   = useState(() => localStorage.getItem("gb_token"));
  const [items, setItems]   = useState([]);
  const [loading, setLoading] = useState(false);
  const [view, setView]     = useState({ kind: "home" });
  const [toast, setToast]   = useState(null);
  const [error, setError]   = useState(null);

  // Handle Telegram OAuth redirect on first render
  useEffect(() => {
    handleTelegramCallback(setToken, setError);
  }, []);

  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2400);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("gb_token");
    setToken(null);
    setItems([]);
    setView({ kind: "home" });
  }, []);

  // Fetch files whenever token changes (login) or after mutations
  const fetchFiles = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [pendingRes, savedRes] = await Promise.all([
        apiFetch("/files?state=pending", token),
        apiFetch("/files?state=saved", token),
      ]);
      if (pendingRes.status === 401 || savedRes.status === 401) { logout(); return; }
      const [pending, saved] = await Promise.all([pendingRes.json(), savedRes.json()]);
      const normalize = (meta, state) => ({
        id:      meta.file_id,
        name:    `file-${meta.file_id.slice(0, 8)}.png`,
        source:  meta.source,
        state,
        stripped: meta.stripped ?? [],
        hue:     fileHue(meta.file_id),
        fmt:     `${(meta.source_format ?? "").toUpperCase()} → PNG`,
      });
      setItems([
        ...pending.map(m => normalize(m, "pending")),
        ...saved.map(m => normalize(m, "saved")),
      ]);
    } catch {
      setError("Could not reach the GuardBox server.");
    } finally {
      setLoading(false);
    }
  }, [token, logout]);

  useEffect(() => { fetchFiles(); }, [fetchFiles]);

  const act = useCallback(async (id, action) => {
    const method = action === "delete" ? "DELETE" : "POST";
    const path   = action === "delete" ? `/files/${id}` : `/files/${id}/save`;
    await apiFetch(path, token, { method });
    setView({ kind: "home" });
    showToast(action === "delete" ? "Deleted. Nothing kept." : "Saved.");
    fetchFiles();
  }, [token, fetchFiles, showToast]);

  const counts = useMemo(() => ({
    pending:  items.filter(i => i.state === "pending").length,
    saved:    items.filter(i => i.state === "saved").length,
    threats:  items.filter(i => (i.stripped?.length ?? 0) > 0).length,
    bySource: {
      share_sheet:  items.filter(i => i.source === "share_sheet").length,
      telegram_bot: items.filter(i => i.source === "telegram_bot").length,
    },
  }), [items]);

  if (!token) {
    return <LoginScreen error={error} onLogin={() => { window.location.href = telegramLoginUrl(); }} />;
  }

  return (
    <div style={{ minHeight: "100vh", background: C.bgGrad, color: C.ink, fontFamily: FONT_BODY, padding: "0 0 90px" }}>
      <style>{`
        *{box-sizing:border-box}
        @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        @keyframes pulse{0%,100%{opacity:.55}50%{opacity:1}}
        @keyframes scan{from{transform:translateY(-100%)}to{transform:translateY(2400%)}}
        .gb-rise{animation:rise .35s ease backwards}
        .gb-tap{transition:transform .12s,border-color .2s,background .2s;cursor:pointer;-webkit-tap-highlight-color:transparent}
        .gb-tap:hover{transform:translateY(-2px);border-color:${C.lineHi}!important}
        .gb-tap:active{transform:translateY(0)}
        :focus-visible{outline:2px solid ${C.safe};outline-offset:3px;border-radius:8px}
        @media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
      `}</style>

      <div style={{ maxWidth: 640, margin: "0 auto", padding: "0 18px" }}>
        <Header onLogout={logout} loading={loading} />

        {view.kind === "home" && (
          <Home
            counts={counts}
            onOpenFolder={(src) => setView({ kind: "folder", source: src })}
            onClearAll={async () => {
              await Promise.all(items.map(i => apiFetch(`/files/${i.id}`, token, { method: "DELETE" })));
              showToast("Cleared.");
              fetchFiles();
            }}
          />
        )}

        {view.kind === "folder" && (
          <Folder
            source={view.source}
            items={items.filter(i => i.source === view.source)}
            onBack={() => setView({ kind: "home" })}
            onOpenFile={(id) => setView({ kind: "viewer", id })}
          />
        )}
      </div>

      <FAB onClick={() => showToast("Forward an image to @GuardBoxBot on Telegram, or share from WhatsApp.")} />

      {view.kind === "viewer" && (
        <Viewer
          it={items.find(i => i.id === view.id)}
          onClose={() => setView({ kind: "home" })}
          onAct={act}
        />
      )}

      {toast && (
        <div style={{ position: "fixed", left: "50%", bottom: 30, transform: "translateX(-50%)", background: "#10241f", border: `1px solid ${C.lineHi}`, padding: "11px 18px", borderRadius: 10, fontSize: 13, fontFamily: FONT_MONO, color: C.ink, animation: "rise .25s ease", zIndex: 80 }}>
          {toast}
        </div>
      )}
    </div>
  );
}

/* ===================== LOGIN SCREEN ===================== */
function LoginScreen({ error, onLogin }) {
  return (
    <div style={{ minHeight: "100vh", background: C.bgGrad, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 28, padding: 24 }}>
      <style>{`*{box-sizing:border-box}@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}.gb-tap{transition:transform .12s;cursor:pointer;-webkit-tap-highlight-color:transparent}.gb-tap:hover{transform:translateY(-2px)}.gb-tap:active{transform:translateY(0)}`}</style>
      <CubeMark />
      <div style={{ fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 28, letterSpacing: "-0.02em", color: C.ink }}>
        Guard<span style={{ color: C.safe }}>Box</span>
      </div>
      <div style={{ fontSize: 14, color: C.inkDim, textAlign: "center", maxWidth: 280, lineHeight: 1.6 }}>
        CDR-sanitised files from Telegram and WhatsApp — originals never touch your device.
      </div>
      {error && (
        <div style={{ fontSize: 13, color: C.danger, background: C.dangerDim, border: `1px solid ${C.danger}`, borderRadius: 10, padding: "10px 16px" }}>{error}</div>
      )}
      <button className="gb-tap" onClick={onLogin}
        style={{ background: C.safe, border: "none", color: "#04231a", fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 15, padding: "14px 32px", borderRadius: 14, display: "flex", alignItems: "center", gap: 10 }}>
        <ShieldIcon color="#04231a" /> Continue with Telegram
      </button>
    </div>
  );
}

/* ===================== HEADER ===================== */
function Header({ onLogout, loading }) {
  return (
    <header style={{ padding: "20px 0 8px", display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: 8 }}>
      <div style={{ justifySelf: "start", fontFamily: FONT_MONO, fontSize: 12, color: loading ? C.amber : C.inkFaint }}>
        {loading ? "syncing…" : ""}
      </div>

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
        <CubeMark />
        <div style={{ fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 22, letterSpacing: "-0.02em", color: C.inkFaint }}>
          Guard<span style={{ color: C.safe }}>Box</span>
        </div>
      </div>

      <button onClick={onLogout} className="gb-tap"
        style={{ background: "transparent", border: `1px solid ${C.line}`, color: C.inkDim, fontFamily: FONT_MONO, fontSize: 12, padding: "7px 12px", borderRadius: 8, justifySelf: "end" }}>
        Log out
      </button>
    </header>
  );
}

/* ===================== HOME ===================== */
function Home({ counts, onOpenFolder, onClearAll }) {
  return (
    <div className="gb-rise" style={{ display: "flex", flexDirection: "column", gap: 22, marginTop: 26 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        <Stat label="Saved"   value={counts.saved}   icon={<CheckCircleIcon c={C.safe}/>}   tone="safe" />
        <Stat label="Pending" value={counts.pending} icon={<SpinnerIcon     c={C.amber}/>}  tone="amber" />
        <Stat label="Threats" value={counts.threats} icon={<AlertCircleIcon c={C.danger}/>} tone="danger" />
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
        <h2 style={{ margin: 0, fontFamily: FONT_DISPLAY, fontWeight: 600, fontSize: 16, color: C.ink, letterSpacing: "-0.01em" }}>Your Images</h2>
        <button onClick={onClearAll} className="gb-tap" style={{ background: "transparent", border: "none", color: C.inkDim, fontFamily: FONT_MONO, fontSize: 11.5, display: "flex", alignItems: "center", gap: 6, padding: 4 }}>
          <TrashIcon /> Clear all
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <SourceCard label="WhatsApp" count={counts.bySource.share_sheet}  icon={<ChatBubbleIcon />} source="share_sheet"  onOpen={() => onOpenFolder("share_sheet")} />
        <SourceCard label="Telegram" count={counts.bySource.telegram_bot} icon={<PaperPlaneIcon />} source="telegram_bot" onOpen={() => onOpenFolder("telegram_bot")} />
      </div>
    </div>
  );
}

function Stat({ label, value, icon, tone }) {
  const ringBg = tone === "safe" ? C.safeDim : tone === "amber" ? "rgba(232,180,80,0.10)" : C.dangerDim;
  return (
    <div className="gb-rise" style={{ background: C.panel, border: `1px solid ${C.line}`, borderRadius: 14, padding: "14px 14px 12px", display: "flex", flexDirection: "column", gap: 6, minHeight: 78 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ width: 22, height: 22, borderRadius: 99, background: ringBg, display: "grid", placeItems: "center", flexShrink: 0 }}>{icon}</span>
        <span style={{ fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 22, lineHeight: 1, color: C.ink }}>{value}</span>
      </div>
      <span style={{ fontSize: 12.5, color: C.inkDim, marginLeft: 30 }}>{label}</span>
    </div>
  );
}

function SourceCard({ label, count, icon, onOpen }) {
  return (
    <button className="gb-tap" onClick={onOpen}
      style={{ background: C.panel, border: `1px solid ${C.line}`, borderRadius: 14, padding: "13px 12px", textAlign: "left", color: C.ink, position: "relative", minHeight: 82, display: "flex", flexDirection: "column", gap: 8, fontFamily: FONT_BODY }}>
      <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
        <span style={{ width: 28, height: 28, borderRadius: 8, background: C.safeDim, display: "grid", placeItems: "center", color: C.safe, flexShrink: 0 }}>{icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 13.5, color: C.safe, lineHeight: 1.15 }}>{label}</div>
          <div style={{ fontSize: 11, color: C.inkDim, marginTop: 3, fontFamily: FONT_MONO }}>{count} image{count === 1 ? "" : "s"}</div>
        </div>
      </div>
      <span style={{ position: "absolute", top: 12, right: 10, color: count > 0 ? C.safe : C.inkFaint }}><CheckRingIcon /></span>
    </button>
  );
}

/* ===================== FOLDER VIEW ===================== */
function Folder({ source, items, onBack, onOpenFile }) {
  return (
    <div className="gb-rise" style={{ marginTop: 26, display: "flex", flexDirection: "column", gap: 14 }}>
      <button onClick={onBack} className="gb-tap" style={{ background: "transparent", border: "none", color: C.inkDim, fontSize: 13, display: "flex", alignItems: "center", gap: 6, padding: "4px 0" }}>← Back</button>
      <h2 style={{ margin: 0, fontFamily: FONT_DISPLAY, fontWeight: 600, fontSize: 18 }}>
        {SOURCE_LABEL[source] ?? source}
        <span style={{ color: C.inkFaint, fontFamily: FONT_MONO, fontSize: 13, fontWeight: 400, marginLeft: 6 }}>{items.length}</span>
      </h2>

      {items.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: C.inkFaint, fontSize: 13 }}>
          No images from {SOURCE_LABEL[source] ?? source} yet.
          {source === "telegram_bot" && <div style={{ marginTop: 8, fontSize: 12 }}>Forward an image to <b style={{ color: C.ink }}>@GuardBoxBot</b>.</div>}
          {source === "share_sheet"  && <div style={{ marginTop: 8, fontSize: 12 }}>Share an image to GuardBox from WhatsApp.</div>}
        </div>
      ) : (
        items.map((it, i) => (
          <button key={it.id} onClick={() => onOpenFile(it.id)} className="gb-tap"
            style={{ background: C.panel, border: `1px solid ${C.line}`, borderRadius: 12, padding: 12, display: "flex", gap: 12, alignItems: "center", textAlign: "left", color: C.ink, animationDelay: `${i * 50}ms` }}>
            <Thumb hue={it.hue} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13.5, fontWeight: 600, fontFamily: FONT_MONO, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{it.name}</div>
              <div style={{ fontSize: 11, color: C.inkFaint, fontFamily: FONT_MONO, marginTop: 3 }}>{it.fmt}</div>
              <div style={{ fontSize: 11, color: C.safe, marginTop: 5, display: "flex", alignItems: "center", gap: 5, fontFamily: FONT_MONO }}>
                <DotIcon /> {it.stripped.length} stripped
              </div>
            </div>
            <ChevronIcon />
          </button>
        ))
      )}
    </div>
  );
}

/* ===================== VIEWER MODAL ===================== */
function Viewer({ it, onClose, onAct }) {
  if (!it) return null;
  const claim =
    it.source === "telegram_bot"
      ? "GuardBox receives the file directly from Telegram's servers — it never travels through your device. You view a screenshot of the reconstructed clean copy in the app — the file itself never travels to your phone."
      : "GuardBox doesn't save the original to your gallery, doesn't keep it in GuardBox's own storage, and doesn't decode it on your phone. WhatsApp briefly holds it in its own private storage in order to share it — that part is outside GuardBox's control. You view a screenshot of the reconstructed clean copy in the app — the file itself is never sent to your phone.";

  return (
    <div role="dialog" aria-modal="true" onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(2,8,7,0.85)", backdropFilter: "blur(6px)", zIndex: 60, display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
      <div onClick={e => e.stopPropagation()}
        style={{ width: "100%", maxWidth: 480, background: "#0a1916", borderTop: `1px solid ${C.line}`, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: "10px 0 22px", animation: "rise .3s ease", maxHeight: "94vh", overflowY: "auto" }}>
        <div style={{ width: 38, height: 4, background: C.line, borderRadius: 99, margin: "0 auto 16px" }} />

        <div style={{ padding: "0 18px" }}>
          <div style={{ fontFamily: FONT_MONO, fontSize: 10.5, color: C.inkFaint, display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span>CONTAINMENT VIEW</span>
            <span style={{ color: C.safe }}>● SAFE COPY</span>
          </div>
          <ContainmentFrame hue={it.hue} />
          <div style={{ fontWeight: 600, fontSize: 15, marginTop: 14, fontFamily: FONT_MONO, color: C.inkDim }}>{it.name}</div>
        </div>

        <div style={{ margin: "16px 18px", background: "rgba(0,0,0,0.25)", border: `1px solid ${C.line}`, borderRadius: 12, overflow: "hidden" }}>
          <KV k="Origin"   v={`forwarded via ${SOURCE_LABEL[it.source] ?? it.source}`} />
          <KV k="Method"   v="Content Disarm & Reconstruction" accent />
          <KV k="Pipeline" v={`${it.fmt} · decoded in sandbox · rebuilt fresh`} mono />
          <div style={{ padding: "11px 14px" }}>
            <div style={{ fontFamily: FONT_MONO, fontSize: 10.5, color: C.inkFaint, marginBottom: 8 }}>STRIPPED ({it.stripped.length})</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {it.stripped.length === 0
                ? <span style={{ fontFamily: FONT_MONO, fontSize: 11, color: C.inkFaint }}>none detected</span>
                : it.stripped.map(s => (
                    <span key={s} style={{ fontFamily: FONT_MONO, fontSize: 10.5, color: C.amber, background: "rgba(232,180,80,0.10)", border: "1px solid rgba(232,180,80,0.25)", padding: "3px 8px", borderRadius: 6 }}>− {s}</span>
                  ))
              }
            </div>
          </div>
        </div>

        <div style={{ padding: "0 18px" }}>
          <div style={{ fontSize: 12.5, color: C.inkDim, marginBottom: 12, textAlign: "center" }}>{claim}</div>
          <div style={{ display: "flex", gap: 11 }}>
            <button className="gb-tap" onClick={() => onAct(it.id, "delete")}
              style={{ flex: 1, background: "transparent", border: `1px solid ${C.line}`, color: C.inkDim, padding: 14, borderRadius: 12, fontSize: 14, fontWeight: 600 }}>
              Delete now
            </button>
            <button className="gb-tap" onClick={() => onAct(it.id, "save")}
              style={{ flex: 1, background: C.safe, border: `1px solid ${C.safe}`, color: "#04231a", padding: 14, borderRadius: 12, fontSize: 14, fontWeight: 700 }}>
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ContainmentFrame({ hue }) {
  const [revealed, setRevealed] = useState(false);
  useEffect(() => { const t = setTimeout(() => setRevealed(true), 450); return () => clearTimeout(t); }, []);
  return (
    <div style={{ position: "relative", borderRadius: 14, overflow: "hidden", border: `1px solid ${C.line}`, background: "repeating-linear-gradient(45deg, #0c211c, #0c211c 10px, #0a1916 10px, #0a1916 20px)", aspectRatio: "4/3" }}>
      <div style={{ position: "absolute", inset: 0, opacity: revealed ? 1 : 0, transition: "opacity .6s ease", background: `linear-gradient(135deg, hsl(${hue} 55% 45%), hsl(${(hue + 60) % 360} 50% 30%))` }} />
      {!revealed && (
        <>
          <div style={{ position: "absolute", left: 0, right: 0, height: "8%", background: `linear-gradient(${C.safe}00, ${C.safe}88, ${C.safe}00)`, animation: "scan 1.6s linear infinite" }} />
          <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", fontFamily: FONT_MONO, fontSize: 11, color: C.safe }}>reconstructing pixels…</div>
        </>
      )}
      {["tl","tr","bl","br"].map(c => (
        <span key={c} style={{ position: "absolute", width: 14, height: 14, [c.includes("t") ? "top" : "bottom"]: 8, [c.includes("l") ? "left" : "right"]: 8, [`border${c.includes("t") ? "Top" : "Bottom"}${c.includes("l") ? "Left" : "Right"}`]: `2px solid ${C.safe}` }} />
      ))}
    </div>
  );
}

function KV({ k, v, mono, accent }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "11px 14px", borderBottom: `1px solid ${C.line}` }}>
      <span style={{ fontFamily: FONT_MONO, fontSize: 10.5, color: C.inkFaint }}>{k.toUpperCase()}</span>
      <span style={{ fontSize: 12, textAlign: "right", color: accent ? C.safe : C.ink, fontFamily: mono ? FONT_MONO : FONT_BODY, fontWeight: accent ? 600 : 400 }}>{v}</span>
    </div>
  );
}

/* ===================== FAB ===================== */
function FAB({ onClick }) {
  return (
    <button onClick={onClick} aria-label="Add"
      style={{ position: "fixed", right: 22, bottom: 22, width: 52, height: 52, borderRadius: 99, background: C.safe, border: "none", boxShadow: "0 8px 22px rgba(52,224,161,0.35)", cursor: "pointer", display: "grid", placeItems: "center", zIndex: 40 }}>
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="#04231a" strokeWidth="2.6" strokeLinecap="round"/></svg>
    </button>
  );
}

/* ===================== ICONS ===================== */
function ShieldIcon({ color = C.safe }) { return (<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 3l8 3v5c0 5-3.4 8.3-8 10-4.6-1.7-8-5-8-10V6l8-3z" stroke={color} strokeWidth="1.6"/><path d="M9 12l2 2 4-4" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>); }
function CubeMark() { return (<svg width="44" height="44" viewBox="0 0 48 48" fill="none"><path d="M24 6L40 14V34L24 42L8 34V14L24 6Z" fill="#0a2421" stroke={C.safe} strokeWidth="1.8" strokeLinejoin="round"/><path d="M24 6V24M24 24L40 14M24 24L8 14M24 24V42" stroke={C.safe} strokeWidth="1.4" strokeLinejoin="round"/></svg>); }
function CheckCircleIcon({c}) { return (<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke={c} strokeWidth="1.8"/><path d="M8 12.5l2.5 2.5L16 9.5" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>); }
function SpinnerIcon({c}) { return (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{animation:"pulse 1.6s ease-in-out infinite"}}><circle cx="12" cy="12" r="9" stroke={c} strokeOpacity="0.3" strokeWidth="1.8"/><path d="M21 12a9 9 0 0 0-9-9" stroke={c} strokeWidth="1.8" strokeLinecap="round"/></svg>); }
function AlertCircleIcon({c}) { return (<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke={c} strokeWidth="1.8"/><path d="M12 8v5M12 16.5v.5" stroke={c} strokeWidth="2" strokeLinecap="round"/></svg>); }
function TrashIcon() { return (<svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" stroke={C.inkDim} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>); }
function ChatBubbleIcon() { return (<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M21 12c0 4.4-4 8-9 8-1.3 0-2.6-.2-3.7-.7L3 21l1.4-4.6C3.5 15.1 3 3 12 4c0-4.4 4-8 9-8s9 3.6 9 8z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/></svg>); }
function PaperPlaneIcon() { return (<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M21 3L3 11l7 3 3 7 8-18z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/><path d="M10 14l5-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>); }
function CheckRingIcon() { return (<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.5"/><path d="M8.5 12.5l2.3 2.3L15.5 10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>); }
function ChevronIcon() { return (<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M9 6l6 6-6 6" stroke={C.inkFaint} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>); }
function DotIcon() { return (<span style={{ width: 5, height: 5, borderRadius: 99, background: C.safe, display: "inline-block" }} />); }
function Thumb({ hue }) {
  return (
    <div style={{ width: 52, height: 52, borderRadius: 10, flexShrink: 0, background: `linear-gradient(135deg, hsl(${hue} 50% 40%), hsl(${(hue + 60) % 360} 45% 26%))`, border: `1px solid ${C.line}`, position: "relative", overflow: "hidden" }}>
      <span style={{ position: "absolute", top: 4, left: 4, width: 7, height: 7, borderTop: `1.5px solid ${C.safe}`, borderLeft: `1.5px solid ${C.safe}` }} />
      <span style={{ position: "absolute", bottom: 4, right: 4, width: 7, height: 7, borderBottom: `1.5px solid ${C.safe}`, borderRight: `1.5px solid ${C.safe}` }} />
    </div>
  );
}
