import React, { useState, useMemo } from "react";

/*  GuardBox — Dashboard
    Layout matches the provided design:
      ┌─── header: logo · wordmark · Login / Traces ───┐
      │  three stat cards: Safe · Scanning · Threats   │
      │  Your Images                       [Clear all] │
      │  three source folders: WhatsApp · Telegram · … │
      │  floating "+" action button                    │
      └────────────────────────────────────────────────┘
    Tapping a source folder drills into that source's files.
    Tapping a file opens the containment viewer (Save / Delete).
    Storage is still folder-based: `pending/{user_id}/` + `saved/{user_id}/`
    with each file tagged by `source` — exactly per portability rules.   */

// ---- self-hosted font stack only — no Google Fonts (per portability rules)
const FONT_DISPLAY = '"Space Grotesk", "Segoe UI", system-ui, sans-serif';
const FONT_BODY = '"Inter", system-ui, sans-serif';
const FONT_MONO = '"JetBrains Mono", "SF Mono", ui-monospace, monospace';

const C = {
  bg: "#06120f",
  bgGrad: "radial-gradient(ellipse at 50% 0%, #0a2421 0%, #06120f 55%)",
  panel: "rgba(255,255,255,0.04)",
  panelHi: "rgba(255,255,255,0.07)",
  line: "rgba(255,255,255,0.08)",
  lineHi: "rgba(52,224,161,0.35)",
  ink: "#eaf2f0",
  inkDim: "#9eb3b0",
  inkFaint: "#5d7672",
  safe: "#34e0a1",
  safeDim: "rgba(52,224,161,0.12)",
  amber: "#e8b450",
  danger: "#ff6b6b",
  dangerDim: "rgba(255,107,107,0.12)",
};

// ----- mock data (real app: GET /files; each row tagged by `source`) -----
const SEED = [
  { id: "f1", name: "IMG-2026-0619.jpg",      source: "telegram", state: "safe",     stripped: ["EXIF", "GPS", "ICC"], received: "just now",   hue: 168, fmt: "JPEG → PNG", sizeIn: "2.4 MB", sizeOut: "1.1 MB" },
  { id: "f2", name: "scan_document.png",       source: "telegram", state: "safe",     stripped: ["EXIF", "thumbnail"],   received: "4m ago",      hue: 28,  fmt: "PNG → PNG",  sizeIn: "5.1 MB", sizeOut: "2.0 MB" },
  { id: "f3", name: "receipt.jpg",              source: "telegram", state: "safe",     stripped: ["EXIF", "GPS"],         received: "2h ago",      hue: 200, fmt: "JPEG → PNG", sizeIn: "880 KB", sizeOut: "640 KB" },
];

export default function GuardBoxDashboard() {
  const [items, setItems] = useState(SEED);
  const [view, setView] = useState({ kind: "home" });   // home | folder | viewer
  const [toast, setToast] = useState(null);

  const counts = useMemo(() => ({
    safe:     items.filter(i => i.state === "safe").length,
    scanning: items.filter(i => i.state === "scanning").length,
    threats:  items.filter(i => (i.stripped?.length ?? 0) > 0 && i.state === "safe").length,
    bySource: {
      whatsapp: items.filter(i => i.source === "whatsapp").length,
      telegram: items.filter(i => i.source === "telegram").length,
      other:    items.filter(i => i.source === "other").length,
    },
  }), [items]);

  const act = (id, action) => {
    setItems(prev => action === "delete" ? prev.filter(i => i.id !== id) : prev);
    setView({ kind: "home" });
    setToast(action === "delete" ? "Deleted. Nothing kept." : "Saved.");
    setTimeout(() => setToast(null), 2400);
  };

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
        <Header onLogin={() => setToast("Login flow → Telegram OAuth")} onTraces={() => setToast("Traces (logs) → coming soon")} />

        {view.kind === "home" && (
          <Home counts={counts} onOpenFolder={(src) => setView({ kind: "folder", source: src })} onClearAll={() => { setItems([]); setToast("Cleared."); setTimeout(() => setToast(null), 1800); }} />
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

      {/* Floating action button */}
      <FAB onClick={() => setToast("Add source → Telegram bot · Share to GuardBox · Connect storage")} />

      {/* Viewer modal */}
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

/* ===================== HEADER ===================== */
function Header({ onLogin, onTraces }) {
  return (
    <header style={{ padding: "20px 0 8px", display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: 8 }}>
      <button onClick={onLogin} className="gb-tap" style={{ background: "transparent", border: "none", color: C.safe, fontFamily: FONT_MONO, fontSize: 12.5, display: "flex", alignItems: "center", gap: 8, padding: "8px 4px", justifySelf: "start" }}>
        <ShieldIcon /> Login
      </button>

      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
        <CubeMark />
        <div style={{ fontFamily: FONT_DISPLAY, fontWeight: 700, fontSize: 22, letterSpacing: "-0.02em", color: C.inkFaint, position: "relative" }}>
          Guard<span style={{ color: C.safe }}>Box</span>
        </div>
      </div>

      <button onClick={onTraces} className="gb-tap" style={{ background: "rgba(255,255,255,0.06)", border: `1px solid ${C.line}`, color: C.ink, fontFamily: FONT_MONO, fontSize: 12, padding: "7px 12px", borderRadius: 8, display: "flex", alignItems: "center", gap: 7, justifySelf: "end" }}>
        <span style={{ color: C.safe }}>{">_"}</span> Traces
      </button>
    </header>
  );
}

/* ===================== HOME ===================== */
function Home({ counts, onOpenFolder, onClearAll }) {
  return (
    <div className="gb-rise" style={{ display: "flex", flexDirection: "column", gap: 22, marginTop: 26 }}>
      {/* stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        <Stat label="Safe"     value={counts.safe}     icon={<CheckCircleIcon  c={C.safe}/>}    tone="safe" />
        <Stat label="Scanning" value={counts.scanning} icon={<SpinnerIcon      c={C.amber}/>}  tone="amber" />
        <Stat label="Threats"  value={counts.threats}  icon={<AlertCircleIcon  c={C.danger}/>} tone="danger" />
      </div>

      {/* section header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
        <h2 style={{ margin: 0, fontFamily: FONT_DISPLAY, fontWeight: 600, fontSize: 16, color: C.ink, letterSpacing: "-0.01em" }}>
          Your Images
        </h2>
        <button onClick={onClearAll} className="gb-tap" style={{ background: "transparent", border: "none", color: C.inkDim, fontFamily: FONT_MONO, fontSize: 11.5, display: "flex", alignItems: "center", gap: 6, padding: 4 }}>
          <TrashIcon /> Clear all
        </button>
      </div>

      {/* three source folders */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        <SourceCard
          label="WhatsApp"
          count={counts.bySource.whatsapp}
          icon={<ChatBubbleIcon />}
          source="whatsapp"
          onOpen={() => onOpenFolder("whatsapp")}
        />
        <SourceCard
          label="Telegram"
          count={counts.bySource.telegram}
          icon={<PaperPlaneIcon />}
          source="telegram"
          onOpen={() => onOpenFolder("telegram")}
        />
        <SourceCard
          label="Other"
          count={counts.bySource.other}
          icon={<ImageStackIcon />}
          source="other"
          onOpen={() => onOpenFolder("other")}
        />
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

function SourceCard({ label, count, icon, source, onOpen }) {
  return (
    <button className="gb-tap" onClick={onOpen}
      style={{ background: C.panel, border: `1px solid ${C.line}`, borderRadius: 14, padding: "13px 12px", textAlign: "left", color: C.ink, position: "relative", minHeight: 82, display: "flex", flexDirection: "column", gap: 8, fontFamily: FONT_BODY }}>
      <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
        <span style={{ width: 28, height: 28, borderRadius: 8, background: C.safeDim, display: "grid", placeItems: "center", color: C.safe, flexShrink: 0 }}>
          {icon}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 13.5, color: C.safe, lineHeight: 1.15, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{label}</div>
          <div style={{ fontSize: 11, color: C.inkDim, marginTop: 3, fontFamily: FONT_MONO }}>{count} image{count === 1 ? "" : "s"}</div>
        </div>
      </div>
      <span style={{ position: "absolute", top: 12, right: 10, color: count > 0 ? C.safe : C.inkFaint }}>
        <CheckRingIcon />
      </span>
    </button>
  );
}

/* ===================== FOLDER VIEW ===================== */
function Folder({ source, items, onBack, onOpenFile }) {
  const labels = { whatsapp: "WhatsApp", telegram: "Telegram", other: "Other" };
  return (
    <div className="gb-rise" style={{ marginTop: 26, display: "flex", flexDirection: "column", gap: 14 }}>
      <button onClick={onBack} className="gb-tap" style={{ background: "transparent", border: "none", color: C.inkDim, fontSize: 13, display: "flex", alignItems: "center", gap: 6, padding: "4px 0" }}>
        ← Back
      </button>
      <h2 style={{ margin: 0, fontFamily: FONT_DISPLAY, fontWeight: 600, fontSize: 18 }}>{labels[source]} <span style={{ color: C.inkFaint, fontFamily: FONT_MONO, fontSize: 13, fontWeight: 400, marginLeft: 6 }}>{items.length}</span></h2>

      {items.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: C.inkFaint, fontSize: 13 }}>
          No images from {labels[source]} yet.
          {source === "telegram" && <div style={{ marginTop: 8, fontSize: 12 }}>Forward an image to <b style={{ color: C.ink }}>@GuardBoxBot</b>.</div>}
          {source === "whatsapp" && <div style={{ marginTop: 8, fontSize: 12 }}>Share an image to GuardBox from WhatsApp.</div>}
        </div>
      ) : (
        items.map((it, i) => (
          <button key={it.id} onClick={() => onOpenFile(it.id)} className="gb-tap"
            style={{ background: C.panel, border: `1px solid ${C.line}`, borderRadius: 12, padding: 12, display: "flex", gap: 12, alignItems: "center", textAlign: "left", color: C.ink, animationDelay: `${i * 50}ms` }}>
            <Thumb hue={it.hue} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{it.name}</div>
              <div style={{ fontSize: 11, color: C.inkFaint, fontFamily: FONT_MONO, marginTop: 3 }}>{it.fmt} · {it.received}</div>
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
  const claim = it.source === "telegram"
    ? "Original never reached your device."
    : "Original never decoded on your device.";
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
          <div style={{ fontWeight: 600, fontSize: 15, marginTop: 14, fontFamily: FONT_DISPLAY }}>{it.name}</div>
        </div>

        <div style={{ margin: "16px 18px", background: "rgba(0,0,0,0.25)", border: `1px solid ${C.line}`, borderRadius: 12, overflow: "hidden" }}>
          <KV k="Origin"    v={`forwarded via ${it.source}`} />
          <KV k="Method"    v="Content Disarm & Reconstruction" accent />
          <KV k="Pipeline"  v={`${it.fmt} · decoded in sandbox · rebuilt fresh`} mono />
          <KV k="Size"      v={`${it.sizeIn} → ${it.sizeOut}`} mono />
          <div style={{ padding: "11px 14px" }}>
            <div style={{ fontFamily: FONT_MONO, fontSize: 10.5, color: C.inkFaint, marginBottom: 8 }}>STRIPPED ({it.stripped.length})</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {it.stripped.map(s => (
                <span key={s} style={{ fontFamily: FONT_MONO, fontSize: 10.5, color: C.amber, background: "rgba(232,180,80,0.10)", border: "1px solid rgba(232,180,80,0.25)", padding: "3px 8px", borderRadius: 6 }}>− {s}</span>
              ))}
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
  React.useEffect(() => { const t = setTimeout(() => setRevealed(true), 450); return () => clearTimeout(t); }, []);
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
        <span key={c} style={{
          position: "absolute", width: 14, height: 14,
          [c.includes("t") ? "top" : "bottom"]: 8,
          [c.includes("l") ? "left" : "right"]: 8,
          [`border${c.includes("t") ? "Top" : "Bottom"}${c.includes("l") ? "Left" : "Right"}`]: `2px solid ${C.safe}`,
        }} />
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

/* ===================== ICONS (inline SVG, no deps) ===================== */
function ShieldIcon() { return (<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 3l8 3v5c0 5-3.4 8.3-8 10-4.6-1.7-8-5-8-10V6l8-3z" stroke={C.safe} strokeWidth="1.6"/><path d="M9 12l2 2 4-4" stroke={C.safe} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>);}
function CubeMark() { return (<svg width="44" height="44" viewBox="0 0 48 48" fill="none"><path d="M24 6L40 14V34L24 42L8 34V14L24 6Z" fill="#0a2421" stroke={C.safe} strokeWidth="1.8" strokeLinejoin="round"/><path d="M24 6V24M24 24L40 14M24 24L8 14M24 24V42" stroke={C.safe} strokeWidth="1.4" strokeLinejoin="round"/></svg>);}
function CheckCircleIcon({c}) { return (<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke={c} strokeWidth="1.8"/><path d="M8 12.5l2.5 2.5L16 9.5" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>);}
function SpinnerIcon({c}) { return (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{animation:"pulse 1.6s ease-in-out infinite"}}><circle cx="12" cy="12" r="9" stroke={c} strokeOpacity="0.3" strokeWidth="1.8"/><path d="M21 12a9 9 0 0 0-9-9" stroke={c} strokeWidth="1.8" strokeLinecap="round"/></svg>);}
function AlertCircleIcon({c}) { return (<svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke={c} strokeWidth="1.8"/><path d="M12 8v5M12 16.5v.5" stroke={c} strokeWidth="2" strokeLinecap="round"/></svg>);}
function TrashIcon() { return (<svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13" stroke={C.inkDim} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>);}
function ChatBubbleIcon() { return (<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M21 12c0 4.4-4 8-9 8-1.3 0-2.6-.2-3.7-.7L3 21l1.4-4.6C3.5 15.1 3 13.6 3 12c0-4.4 4-8 9-8s9 3.6 9 8z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/></svg>);}
function PaperPlaneIcon() { return (<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M21 3L3 11l7 3 3 7 8-18z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/><path d="M10 14l5-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>);}
function ImageStackIcon() { return (<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="3" y="6" width="15" height="13" rx="2" stroke="currentColor" strokeWidth="1.6"/><circle cx="8.5" cy="11" r="1.3" fill="currentColor"/><path d="M3 17l5-4 4 3 3-2 3 2" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/><path d="M7 6V5a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-1" stroke="currentColor" strokeWidth="1.6" strokeOpacity="0.5"/></svg>);}
function CheckRingIcon() { return (<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.5"/><path d="M8.5 12.5l2.3 2.3L15.5 10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>);}
function ChevronIcon() { return (<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M9 6l6 6-6 6" stroke={C.inkFaint} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>);}
function DotIcon() { return (<span style={{ width: 5, height: 5, borderRadius: 99, background: C.safe, display: "inline-block" }} />);}
function Thumb({ hue }) {
  return (
    <div style={{ width: 52, height: 52, borderRadius: 10, flexShrink: 0, background: `linear-gradient(135deg, hsl(${hue} 50% 40%), hsl(${(hue + 60) % 360} 45% 26%))`, border: `1px solid ${C.line}`, position: "relative", overflow: "hidden" }}>
      <span style={{ position: "absolute", top: 4, left: 4, width: 7, height: 7, borderTop: `1.5px solid ${C.safe}`, borderLeft: `1.5px solid ${C.safe}` }} />
      <span style={{ position: "absolute", bottom: 4, right: 4, width: 7, height: 7, borderBottom: `1.5px solid ${C.safe}`, borderRight: `1.5px solid ${C.safe}` }} />
    </div>
  );
}
