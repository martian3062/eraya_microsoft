"use client";
import { useEffect, useRef, useState } from "react";
import L from "leaflet";
// CSS is imported globally in globals.css
// Fix Leaflet default marker icon broken paths in webpack/Next.js
// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

/* ── Domain colours ──────────────────────────────────────────────── */
const DOMAIN_COLOR: Record<string, string> = {
  telecom: "#2dd4bf",
  cloud:   "#60a5fa",
  icu:     "#f472b6",
  edge:    "#fb923c",
};

const SEV_RING: Record<string, string> = {
  critical: "#f87171",
  warning:  "#fbbf24",
  ok:       "#34d399",
  info:     "#a78bfa",
};

/* ── Incident data ───────────────────────────────────────────────── */
export interface Incident {
  id: number;
  lat: number; lng: number;
  city: string; country: string;
  domain: "telecom" | "cloud" | "icu" | "edge";
  severity: "critical" | "warning" | "ok" | "info";
  agent: string;
  msg: string;
  ts: number;
}

const BASE_INCIDENTS: Omit<Incident, "ts">[] = [
  { id:1,  lat:40.71,  lng:-74.01,  city:"New York",     country:"US",  domain:"telecom", severity:"warning",  agent:"Perceiver",  msg:"Tower-7 signal drop — RSRP −94 dBm" },
  { id:2,  lat:51.51,  lng:-0.13,   city:"London",       country:"GB",  domain:"cloud",   severity:"ok",       agent:"Recoverer",  msg:"Pod restart completed — latency restored" },
  { id:3,  lat:35.68,  lng:139.69,  city:"Tokyo",        country:"JP",  domain:"edge",    severity:"critical", agent:"Guardian",   msg:"Injection attempt blocked at edge node" },
  { id:4,  lat:19.08,  lng:72.88,   city:"Mumbai",       country:"IN",  domain:"telecom", severity:"warning",  agent:"Perceiver",  msg:"5G handoff failure rate 12% — monitoring" },
  { id:5,  lat:25.20,  lng:55.27,   city:"Dubai",        country:"AE",  domain:"cloud",   severity:"info",     agent:"Planner",    msg:"Auto-scaling triggered — +3 replicas" },
  { id:6,  lat:37.77,  lng:-122.42, city:"San Francisco",country:"US",  domain:"icu",     severity:"critical", agent:"Perceiver",  msg:"Ward 3A HRV spike — guardian alerted" },
  { id:7,  lat:52.52,  lng:13.41,   city:"Berlin",       country:"DE",  domain:"cloud",   severity:"ok",       agent:"Recoverer",  msg:"Memory leak patched — heap stable" },
  { id:8,  lat:1.35,   lng:103.82,  city:"Singapore",    country:"SG",  domain:"telecom", severity:"ok",       agent:"Planner",    msg:"Network mesh optimised — 14 nodes" },
  { id:9,  lat:48.86,  lng:2.35,    city:"Paris",        country:"FR",  domain:"icu",     severity:"warning",  agent:"Guardian",   msg:"Equipment fault detected — isolating" },
  { id:10, lat:-33.87, lng:151.21,  city:"Sydney",       country:"AU",  domain:"edge",    severity:"warning",  agent:"Perceiver",  msg:"Latency spike 340 ms — rerouting" },
  { id:11, lat:55.75,  lng:37.62,   city:"Moscow",       country:"RU",  domain:"cloud",   severity:"critical", agent:"Guardian",   msg:"Spoofed A2A message intercepted & blocked" },
  { id:12, lat:43.65,  lng:-79.38,  city:"Toronto",      country:"CA",  domain:"telecom", severity:"ok",       agent:"Recoverer",  msg:"Failover completed — SLO 99.3%" },
  { id:13, lat:28.61,  lng:77.21,   city:"Delhi",        country:"IN",  domain:"edge",    severity:"info",     agent:"Planner",    msg:"Traffic rebalanced across 6 edge nodes" },
  { id:14, lat:31.23,  lng:121.47,  city:"Shanghai",     country:"CN",  domain:"cloud",   severity:"warning",  agent:"Perceiver",  msg:"CPU burst 89% — scaling in progress" },
  { id:15, lat:-23.55, lng:-46.63,  city:"São Paulo",    country:"BR",  domain:"telecom", severity:"info",     agent:"Planner",    msg:"Carrier aggregation optimised" },
  { id:16, lat:6.52,   lng:3.38,    city:"Lagos",        country:"NG",  domain:"icu",     severity:"warning",  agent:"Perceiver",  msg:"Vitals monitor offline — failsafe active" },
];

const INCIDENTS: Incident[] = BASE_INCIDENTS.map(i => ({ ...i, ts: Date.now() - Math.random() * 120_000 }));

/* ── Feed items ──────────────────────────────────────────────────── */
interface FeedItem extends Incident { feedId: number; }

function makeFeedItem(src: Incident, feedId: number): FeedItem {
  return { ...src, ts: Date.now(), feedId };
}

function fmtAgo(ts: number) {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s ago`;
  return `${Math.floor(s / 60)}m ago`;
}

/* ── Custom div-icon marker ──────────────────────────────────────── */
function makeIcon(inc: Incident) {
  const col  = DOMAIN_COLOR[inc.domain] ?? "#2dd4bf";
  const ring = SEV_RING[inc.severity]   ?? "#2dd4bf";
  const pulse = inc.severity === "critical" || inc.severity === "warning";
  const html = `
    <div style="position:relative;width:28px;height:28px">
      ${pulse ? `<div style="position:absolute;inset:-4px;border-radius:50%;border:2px solid ${ring};animation:ping 1.6s ease-out infinite;opacity:.6"></div>` : ""}
      <div style="width:28px;height:28px;border-radius:50%;background:${col}22;border:2px solid ${col};display:flex;align-items:center;justify-content:center;font-size:11px">
        ${ inc.domain==="telecom" ? "📡" : inc.domain==="cloud" ? "☁️" : inc.domain==="icu" ? "🏥" : "⚡" }
      </div>
    </div>`;
  return L.divIcon({ html, className: "", iconSize: [28, 28], iconAnchor: [14, 14] });
}

/* ── Component ───────────────────────────────────────────────────── */
export default function MapView() {
  const mapRef   = useRef<L.Map | null>(null);
  const divRef   = useRef<HTMLDivElement>(null);
  const [feed, setFeed] = useState<FeedItem[]>(() =>
    [...INCIDENTS].sort((a, b) => b.ts - a.ts).slice(0, 8).map((i, idx) => makeFeedItem(i, idx))
  );
  const [selected, setSelected] = useState<Incident | null>(null);
  const feedId = useRef(100);

  /* init map once */
  useEffect(() => {
    if (mapRef.current || !divRef.current) return;
    const map = L.map(divRef.current, { zoomControl: false, center: [20, 10], zoom: 2 });
    mapRef.current = map;

    /* CartoDB Dark Matter — no API key */
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>', subdomains: "abcd", maxZoom: 19 }
    ).addTo(map);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    /* add markers */
    INCIDENTS.forEach(inc => {
      const marker = L.marker([inc.lat, inc.lng], { icon: makeIcon(inc) }).addTo(map);
      marker.on("click", () => setSelected(inc));
    });

    return () => { map.remove(); mapRef.current = null; };
  }, []);

  /* live feed — push a new event every 7s */
  useEffect(() => {
    const iv = setInterval(() => {
      const src = INCIDENTS[Math.floor(Math.random() * INCIDENTS.length)];
      setFeed(prev => [makeFeedItem(src, feedId.current++), ...prev].slice(0, 40));
    }, 7000);
    return () => clearInterval(iv);
  }, []);

  const counts = {
    critical: INCIDENTS.filter(i => i.severity === "critical").length,
    warning:  INCIDENTS.filter(i => i.severity === "warning").length,
    ok:       INCIDENTS.filter(i => i.severity === "ok").length,
  };

  return (
    <div className="relative flex h-full w-full overflow-hidden bg-[#060d1a]">
      {/* ping keyframe */}
      <style>{`@keyframes ping{0%{transform:scale(1);opacity:.6}80%,100%{transform:scale(2.2);opacity:0}}`}</style>

      {/* ── Map ── */}
      <div ref={divRef} className="flex-1 h-full z-0" />

      {/* ── KPI bar ── */}
      <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[500] flex gap-2">
        {[
          { label: "Critical", count: counts.critical, col: "#f87171" },
          { label: "Warning",  count: counts.warning,  col: "#fbbf24" },
          { label: "Healthy",  count: counts.ok,        col: "#34d399" },
          { label: "Agents",   count: 16,               col: "#2dd4bf" },
        ].map(k => (
          <div key={k.label}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium"
            style={{ background: "#0c1628cc", border: `1px solid ${k.col}44`, backdropFilter: "blur(8px)" }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: k.col }} />
            <span style={{ color: k.col }}>{k.count}</span>
            <span className="text-white/40">{k.label}</span>
          </div>
        ))}
      </div>

      {/* ── Incident detail popup ── */}
      {selected && (
        <div className="absolute bottom-8 left-4 z-[500] w-64 rounded-xl p-4 text-xs"
          style={{ background: "#0c1628ee", border: `1px solid ${DOMAIN_COLOR[selected.domain]}44`, backdropFilter: "blur(12px)" }}>
          <div className="flex items-start justify-between mb-2">
            <span className="font-semibold text-white/90">{selected.city}, {selected.country}</span>
            <button onClick={() => setSelected(null)} className="text-white/30 hover:text-white/70 text-base leading-none">×</button>
          </div>
          <div className="mb-1" style={{ color: DOMAIN_COLOR[selected.domain] }}>
            {selected.domain.toUpperCase()} · {selected.agent}
          </div>
          <div className="text-white/70 leading-snug">{selected.msg}</div>
          <div className="mt-2 flex items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded-full text-[10px]"
              style={{ background: SEV_RING[selected.severity] + "22", color: SEV_RING[selected.severity] }}>
              {selected.severity}
            </span>
          </div>
        </div>
      )}

      {/* ── News feed panel ── */}
      <div className="w-72 h-full flex flex-col z-[400] shrink-0"
        style={{ background: "#060d1acc", borderLeft: "1px solid rgba(255,255,255,0.07)", backdropFilter: "blur(16px)" }}>

        {/* header */}
        <div className="px-4 py-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
            <span className="text-xs font-semibold text-white/80 tracking-wider uppercase">Live Feed</span>
          </div>
          <p className="text-[10px] text-white/30 mt-0.5">Global agent events · real-time</p>
        </div>

        {/* domain legend */}
        <div className="flex flex-wrap gap-1.5 px-4 py-2 border-b border-white/[0.06]">
          {Object.entries(DOMAIN_COLOR).map(([d, c]) => (
            <span key={d} className="flex items-center gap-1 text-[10px]" style={{ color: c }}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: c }} />
              {d}
            </span>
          ))}
        </div>

        {/* scrollable feed */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5" style={{ scrollbarWidth: "none" }}>
          {feed.map(item => (
            <div key={item.feedId}
              className="rounded-lg px-3 py-2 cursor-pointer transition-all hover:brightness-110"
              style={{ background: DOMAIN_COLOR[item.domain] + "10", borderLeft: `2px solid ${SEV_RING[item.severity]}` }}
              onClick={() => setSelected(item)}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[10px] font-semibold" style={{ color: DOMAIN_COLOR[item.domain] }}>
                  {item.agent} · {item.city}
                </span>
                <span className="text-[9px] text-white/25">{fmtAgo(item.ts)}</span>
              </div>
              <p className="text-[10px] text-white/65 leading-snug line-clamp-2">{item.msg}</p>
              <span className="mt-1 inline-block text-[9px] px-1.5 py-0.5 rounded-full"
                style={{ background: SEV_RING[item.severity] + "20", color: SEV_RING[item.severity] }}>
                {item.severity}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
