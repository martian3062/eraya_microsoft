"use client";
import { useEffect, useRef } from "react";
import { useThemeStore } from "@/store/theme";

const NODES = [
  { id: 0,  cx: 16,  cy: 18,  r: 2.5, im: "im-a", dur: "14s", delay: "0s"   },
  { id: 1,  cx: 46,  cy: 50,  r: 3.5, im: "im-b", dur: "18s", delay: "-3s"  },
  { id: 2,  cx: 88,  cy: 22,  r: 2.5, im: "im-c", dur: "16s", delay: "-7s"  },
  { id: 3,  cx: 124, cy: 62,  r: 4.0, im: "im-d", dur: "20s", delay: "-1s"  },
  { id: 4,  cx: 158, cy: 29,  r: 2.5, im: "im-a", dur: "15s", delay: "-5s"  },
  { id: 5,  cx: 176, cy: 82,  r: 3.5, im: "im-b", dur: "17s", delay: "-9s"  },
  { id: 6,  cx: 68,  cy: 89,  r: 2.5, im: "im-c", dur: "19s", delay: "-2s"  },
  { id: 7,  cx: 108, cy: 101, r: 3.5, im: "im-d", dur: "13s", delay: "-6s"  },
  { id: 8,  cx: 32,  cy: 72,  r: 2.5, im: "im-a", dur: "21s", delay: "-4s"  },
  { id: 9,  cx: 140, cy: 46,  r: 2.5, im: "im-b", dur: "16s", delay: "-8s"  },
  { id: 10, cx: 96,  cy: 55,  r: 3.0, im: "im-c", dur: "15s", delay: "-11s" },
  { id: 11, cx: 170, cy: 53,  r: 2.5, im: "im-d", dur: "18s", delay: "-13s" },
];

const EDGES: [number, number, string, string][] = [
  [0, 1,  "11s", "0s"  ], [1, 2,  "13s", "-2s" ],
  [2, 10, "15s", "-5s" ], [10, 3, "12s", "-8s" ],
  [3, 4,  "14s", "-3s" ], [3, 5,  "16s", "-1s" ],
  [6, 7,  "13s", "-7s" ], [8, 1,  "17s", "-4s" ],
  [9, 3,  "11s", "-9s" ], [10, 9, "15s", "-6s" ],
  [11, 4, "13s", "-2s" ], [6, 10, "18s", "-10s"],
  [0, 8,  "12s", "-3s" ], [7, 5,  "14s", "-7s" ],
];

function edgeLen(a: typeof NODES[0], b: typeof NODES[0]) {
  return Math.hypot(b.cx - a.cx, b.cy - a.cy);
}

export function AnimatedBg() {
  const dark = useThemeStore((s) => s.dark);
  const blob1 = useRef<HTMLDivElement>(null);
  const blob2 = useRef<HTMLDivElement>(null);
  const blob3 = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    let raf = 0;
    let mx = 0.5, my = 0.5;
    let tx = 0.5, ty = 0.5;

    function onMove(e: MouseEvent) {
      tx = e.clientX / window.innerWidth;
      ty = e.clientY / window.innerHeight;
    }

    function tick() {
      mx += (tx - mx) * 0.04;
      my += (ty - my) * 0.04;
      const dx = (mx - 0.5) * 60;
      const dy = (my - 0.5) * 40;
      if (blob1.current) blob1.current.style.transform = `translate(${dx * 0.6}px, ${dy * 0.6}px)`;
      if (blob2.current) blob2.current.style.transform = `translate(${-dx * 0.4}px, ${-dy * 0.4}px)`;
      if (blob3.current) blob3.current.style.transform = `translate(${dx * 0.3}px, ${dy * 0.5}px)`;
      if (svgRef.current)  svgRef.current.style.transform = `translate(${dx * 0.12}px, ${dy * 0.12}px)`;
      raf = requestAnimationFrame(tick);
    }

    window.addEventListener("mousemove", onMove, { passive: true });
    raf = requestAnimationFrame(tick);
    return () => { window.removeEventListener("mousemove", onMove); cancelAnimationFrame(raf); };
  }, []);

  const blobs = dark
    ? {
        b1: { bg: "radial-gradient(circle, #0e4a40 0%, #0a2e3a 50%, transparent 80%)", opacity: 0.38, blur: "blur(60px)" },
        b2: { bg: "radial-gradient(circle, #3d2005 0%, #1e1000 40%, transparent 75%)", opacity: 0.30, blur: "blur(55px)" },
        b3: { bg: "radial-gradient(circle, #093a44 0%, #062e1e 50%, transparent 80%)", opacity: 0.28, blur: "blur(50px)" },
      }
    : {
        b1: { bg: "radial-gradient(circle, #99f6e4 0%, #67e8f9 50%, transparent 80%)", opacity: 0.18, blur: "blur(60px)" },
        b2: { bg: "radial-gradient(circle, #fed7aa 0%, #fde68a 40%, transparent 75%)", opacity: 0.15, blur: "blur(55px)" },
        b3: { bg: "radial-gradient(circle, #a5f3fc 0%, #6ee7b7 50%, transparent 80%)", opacity: 0.13, blur: "blur(50px)" },
      };

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }} aria-hidden>
      <div ref={blob1} className="absolute rounded-full"
        style={{
          width: "60vw", height: "60vw", top: "-20vw", left: "-10vw",
          background: blobs.b1.bg, opacity: blobs.b1.opacity,
          filter: blobs.b1.blur, animation: "blob-a 22s ease-in-out infinite",
          willChange: "transform", transition: "transform 0.1s ease-out, opacity 0.5s ease",
        }} />
      <div ref={blob2} className="absolute rounded-full"
        style={{
          width: "50vw", height: "50vw", bottom: "-15vw", right: "-5vw",
          background: blobs.b2.bg, opacity: blobs.b2.opacity,
          filter: blobs.b2.blur, animation: "blob-b 28s ease-in-out infinite",
          willChange: "transform", transition: "transform 0.1s ease-out, opacity 0.5s ease",
        }} />
      <div ref={blob3} className="absolute rounded-full"
        style={{
          width: "45vw", height: "45vw", top: "35vh", left: "35vw",
          background: blobs.b3.bg, opacity: blobs.b3.opacity,
          filter: blobs.b3.blur, animation: "blob-c 25s ease-in-out infinite",
          willChange: "transform", transition: "transform 0.1s ease-out, opacity 0.5s ease",
        }} />

      {/* Network graph */}
      <svg ref={svgRef} className="absolute inset-0 w-full h-full"
        viewBox="0 0 200 120" preserveAspectRatio="xMidYMid slice"
        style={{ opacity: dark ? 0.28 : 0.18, willChange: "transform", transition: "transform 0.15s ease-out, opacity 0.5s ease" }}
      >
        <defs>
          <radialGradient id="ng-teal" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#14b8a6" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
          </radialGradient>
        </defs>

        {EDGES.map(([fromId, toId, dur, delay], i) => {
          const a = NODES[fromId]; const b = NODES[toId];
          const len = edgeLen(a, b);
          return (
            <line key={`ge-${i}`} x1={a.cx} y1={a.cy} x2={b.cx} y2={b.cy}
              stroke="url(#ng-teal)" strokeWidth="0.4" strokeDasharray={len}
              style={{ animation: `g-step ${dur} linear ${delay} infinite` }} />
          );
        })}

        {EDGES.map(([fromId, toId], i) => {
          const a = NODES[fromId]; const b = NODES[toId];
          return (
            <line key={`bg-${i}`} x1={a.cx} y1={a.cy} x2={b.cx} y2={b.cy}
              stroke="#14b8a6" strokeWidth="0.2" strokeOpacity={dark ? 0.5 : 0.3} />
          );
        })}

        {NODES.map((n, i) => (
          <g key={n.id}
            style={{ animation: `${n.im} ${n.dur} ease-in-out ${n.delay} infinite`,
                     transformOrigin: `${n.cx}px ${n.cy}px`, transformBox: "fill-box" }}
          >
            <circle cx={n.cx} cy={n.cy} r={n.r * 2.5}
              fill={i % 3 === 0 ? "#f97316" : "#14b8a6"} opacity={dark ? 0.2 : 0.12} />
            <circle cx={n.cx} cy={n.cy} r={n.r}
              fill={i % 3 === 0 ? "#f97316" : i % 3 === 1 ? "#14b8a6" : "#06b6d4"} opacity="0.8" />
          </g>
        ))}
      </svg>
    </div>
  );
}
