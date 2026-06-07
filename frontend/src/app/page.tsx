"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { useAuthStore } from "@/store/auth";
import { useThemeStore } from "@/store/theme";
import { Shield, User, ArrowLeft, Mail, Lock, UserPlus, AlertCircle } from "lucide-react";
import { AttractorCanvas } from "@/components/attractor-canvas";

/* ── Live system snippets (constrained x ≤ 50%) ───────────────── */
const SNIPPETS = [
  "perceiver · tier2 · 87ms",   "BLOCKED · R003 · guardian",
  "rsrp: −87.4 dBm",            "planner · groq · 3.1s",
  "self-heal → pod restart",    "cpu: 84.2% → recovering",
  "a2a · msg_id: 7429",         "otel · trace_id: 8c2f…",
  "hrv_alert · ward_4B",        "edge_drop · 5g · n78",
  "anomaly · BLOCKED · killed", "recoverer · rollback · v2.3",
  "kavacha · inject · stopped", "mesh · 12 nodes · 14 edges",
  "slo: 99.1% · compliant",     "cloud · cost +12% · alert",
  "guardian · quarantine · ok", "perceiver · rsrq: −9.2 dB",
];

const SLOTS = [
  {x:4, y:8},{x:38,y:5},{x:20,y:18},{x:46,y:28},{x:9, y:36},
  {x:34,y:48},{x:48,y:42},{x:15,y:58},{x:40,y:64},
  {x:6, y:74},{x:28,y:80},{x:44,y:86},
];

function snippetColor(s: string): string {
  if(/BLOCKED|alert|anomaly|killed|stopped/i.test(s)) return "#f87171";
  if(/ms|dBm|%|ok|compliant/i.test(s))                return "#fbbf24";
  if(/planner|groq/i.test(s))                          return "#a78bfa";
  if(/otel|trace/i.test(s))                            return "#60a5fa";
  return "#2dd4bf";
}

interface SlotState { snippetIdx: number; visible: boolean; }

function LivePreview({ dark }: { dark: boolean }) {
  const [slots, setSlots] = useState<SlotState[]>(() =>
    SLOTS.map((_, i) => ({ snippetIdx: i % SNIPPETS.length, visible: i < 5 }))
  );
  useEffect(() => {
    const iv = setInterval(() => {
      setSlots((prev) => {
        const next = [...prev];
        const i = Math.floor(Math.random() * SLOTS.length);
        next[i] = next[i].visible
          ? { ...next[i], visible: false }
          : { snippetIdx: Math.floor(Math.random() * SNIPPETS.length), visible: true };
        return next;
      });
    }, 1300);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="absolute inset-0 pointer-events-none z-10" aria-hidden>
      {slots.map((slot, i) => {
        const base = snippetColor(SNIPPETS[slot.snippetIdx]);
        /* darken colors slightly for light mode readability */
        const color = dark ? base : base;
        return (
          <span key={i} style={{
            position:"absolute", left:`${SLOTS[i].x}%`, top:`${SLOTS[i].y}%`,
            opacity: slot.visible ? (dark ? 0.78 : 0.65) : 0,
            transform: slot.visible ? "translateY(0)" : "translateY(8px)",
            transition: "opacity 1s ease, transform 1s ease",
            pointerEvents: "none",
            color,
            fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
            fontSize: "10px", letterSpacing: "0.05em", whiteSpace: "nowrap",
            textShadow: dark ? `0 0 12px ${base}55` : `0 0 8px ${base}33`,
          }}>
            {SNIPPETS[slot.snippetIdx]}
          </span>
        );
      })}
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden>
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const { dark, toggle } = useThemeStore();
  const [step, setStep] = useState<"entry" | "name" | "email" | "register">("entry");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  const bgDark  = "linear-gradient(135deg,#08041a 0%,#0c1228 40%,#050f18 70%,#040f0c 100%)";
  const bgLight = "linear-gradient(135deg,#fdfaf4 0%,#fff8f0 35%,#f5f2ff 65%,#eef7ff 100%)";

  function handleOperator() {
    if (!name.trim()) return;
    login({ name: name.trim(), role: "operator" });
    router.push("/dashboard");
  }
  function handleGuest() {
    login({ name: "Guest", role: "guest" });
    router.push("/dashboard");
  }
  async function handleEmailLogin() {
    if (!email || !password) { setAuthError("Enter email and password."); return; }
    setAuthLoading(true); setAuthError("");
    const res = await signIn("credentials", { email, password, redirect: false });
    setAuthLoading(false);
    if (res?.ok) { router.push("/dashboard"); }
    else { setAuthError("Invalid email or password."); }
  }
  async function handleRegister() {
    if (!email || !password) { setAuthError("Enter email and password."); return; }
    if (password.length < 6) { setAuthError("Password must be at least 6 characters."); return; }
    setAuthLoading(true); setAuthError("");
    try {
      const r = await fetch(`${API}/api/eraya-auth/register/`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name: name || email.split("@")[0] }),
      });
      const data = await r.json();
      if (!r.ok) { setAuthError(data.error ?? "Registration failed."); setAuthLoading(false); return; }
      /* auto-login after register */
      const res = await signIn("credentials", { email, password, redirect: false });
      setAuthLoading(false);
      if (res?.ok) router.push("/dashboard");
      else setAuthError("Registered but login failed — try signing in.");
    } catch { setAuthLoading(false); setAuthError("Network error — is the backend running?"); }
  }
  function handleThemeToggle() {
    const next = !dark;
    toggle();
    document.documentElement.classList.toggle("dark", next);
  }

  /* Card glass style switches with theme */
  const cardText    = dark ? "text-white/90"   : "text-slate-800";
  const subText     = dark ? "text-white/38"   : "text-slate-400";
  const glassBorder = dark ? "border-white/12" : "border-slate-200/80";
  const glassBg     = dark ? "bg-white/8"      : "bg-white/70";
  const inputStyle  = dark
    ? "border-white/15 bg-white/10 text-white placeholder:text-white/35 focus:ring-teal-400/60"
    : "border-slate-200 bg-white/85 text-slate-800 placeholder:text-slate-400 focus:ring-teal-400";
  const googleStyle = dark
    ? "border-white/15 bg-white/10 text-white/88 hover:bg-white/16"
    : "border-slate-200 bg-white/90 text-slate-700 hover:bg-white";
  const guestStyle  = dark
    ? "text-white/32 hover:text-white/58 hover:bg-white/8"
    : "text-slate-400 hover:text-slate-600 hover:bg-slate-100/60";

  return (
    <div className="min-h-screen relative overflow-hidden"
      style={{ background: dark ? bgDark : bgLight }}>

      {/* Layer 0 — full-width attractor canvas */}
      <AttractorCanvas />

      {/* Layer 1 — floating snippets */}
      <LivePreview dark={dark} />

      {/* Layer 2 — smooth gradient veil (CSS class handles dark/light) */}
      <div className="login-veil absolute inset-0 pointer-events-none z-20" />

      {/* Layer 3 — bottom fluid blobs spanning full width */}
      <div className="absolute bottom-0 left-0 right-0 pointer-events-none z-[15]" style={{height:"40%"}}>
        <div className="absolute rounded-full" style={{
          bottom:"-60px", left:"5%", width:"44vw", height:"28vw",
          background:"radial-gradient(ellipse,rgba(45,212,191,0.13) 0%,transparent 70%)",
          filter:"blur(48px)", animation:"blob-a 22s ease-in-out infinite",
        }}/>
        <div className="absolute rounded-full" style={{
          bottom:"-40px", left:"30%", width:"32vw", height:"20vw",
          background:"radial-gradient(ellipse,rgba(139,92,246,0.10) 0%,transparent 70%)",
          filter:"blur(40px)", animation:"blob-b 28s ease-in-out infinite",
        }}/>
        <div className="absolute rounded-full" style={{
          bottom:"-50px", right:"8%", width:"36vw", height:"22vw",
          background:"radial-gradient(ellipse,rgba(251,146,60,0.09) 0%,transparent 70%)",
          filter:"blur(52px)", animation:"blob-c 24s ease-in-out infinite",
        }}/>
      </div>

      {/* Layer 4 — logo + theme toggle */}
      <div className="absolute top-6 left-7 z-30 flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-orange-400 to-teal-400 flex items-center justify-center text-white font-bold text-sm shadow-lg">
          E
        </div>
        <span className={`font-semibold text-sm tracking-widest uppercase transition-colors ${dark ? "text-white/60" : "text-slate-600/80"}`}>
          Eraya
        </span>
      </div>
      {/* Theme toggle — top right */}
      <button
        onClick={handleThemeToggle}
        className={`absolute top-6 right-6 z-30 w-8 h-8 rounded-full flex items-center justify-center transition-all
          ${dark ? "text-white/50 hover:text-white/80 hover:bg-white/8" : "text-slate-500 hover:text-slate-800 hover:bg-slate-200/60"}`}
        title={dark ? "Light mode" : "Dark mode"}
      >
        {dark
          ? <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
          : <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        }
      </button>

      {/* Layer 5 — login card */}
      <div className="absolute inset-0 flex items-center justify-center lg:justify-end z-30 px-8 lg:pr-16 lg:pl-0 pointer-events-none">
        <div className={`pointer-events-auto w-full max-w-[295px] space-y-5 rounded-2xl p-7 border backdrop-blur-sm shadow-2xl transition-all
          ${glassBg} ${glassBorder}`}
          style={{ boxShadow: dark ? "0 24px 80px rgba(0,0,0,0.45)" : "0 24px 80px rgba(0,0,0,0.10)" }}>

          {/* Heading */}
          <div>
            <h1 className={`text-xl font-bold tracking-tight ${cardText}`}>Sign in</h1>
            <p className={`text-sm mt-0.5 ${subText}`}>Self-healing agent console</p>
          </div>

          {step === "entry" && (
            <div className="space-y-2.5">
              <button
                onClick={() => setStep("name")}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-medium text-sm hover:from-teal-400 hover:to-cyan-400 transition-all shadow-md shadow-teal-900/20"
              >
                <Shield size={15} />
                Operator
              </button>

              <button
                onClick={() => { setAuthError(""); setStep("email"); }}
                className={`w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl border font-medium text-sm transition-all ${googleStyle}`}
              >
                <Mail size={14} />
                Sign in with Email
              </button>

              <button
                onClick={() => signIn("google")}
                className={`w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl border font-medium text-sm transition-all ${googleStyle}`}
              >
                <GoogleIcon />
                Continue with Google
              </button>

              <button
                onClick={handleGuest}
                className={`w-full px-4 py-2.5 rounded-xl text-sm transition-all ${guestStyle}`}
              >
                <User size={13} className="inline mr-2 opacity-60" />
                Guest
              </button>
            </div>
          )}

          {step === "name" && (
            <div className="space-y-3">
              <input
                autoFocus
                type="text"
                placeholder="Your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleOperator()}
                className={`w-full px-4 py-3 rounded-xl border text-sm focus:outline-none focus:ring-2 transition-all ${inputStyle}`}
              />
              <button
                onClick={handleOperator}
                disabled={!name.trim()}
                className="w-full px-4 py-3 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-medium text-sm hover:from-teal-400 hover:to-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                Enter
              </button>
              <button onClick={() => setStep("entry")} className={`w-full flex items-center justify-center gap-1.5 text-sm transition-colors py-1 ${guestStyle}`}>
                <ArrowLeft size={13} /> Back
              </button>
            </div>
          )}

          {(step === "email" || step === "register") && (
            <div className="space-y-3">
              {authError && (
                <div className="flex items-center gap-2 text-[11px] text-red-500 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl px-3 py-2">
                  <AlertCircle size={12} className="flex-shrink-0" />
                  {authError}
                </div>
              )}

              {step === "register" && (
                <input
                  autoFocus
                  type="text"
                  placeholder="Your name (optional)"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className={`w-full px-4 py-3 rounded-xl border text-sm focus:outline-none focus:ring-2 transition-all ${inputStyle}`}
                />
              )}

              <input
                autoFocus={step === "email"}
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (step === "email" ? handleEmailLogin() : handleRegister())}
                className={`w-full px-4 py-3 rounded-xl border text-sm focus:outline-none focus:ring-2 transition-all ${inputStyle}`}
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (step === "email" ? handleEmailLogin() : handleRegister())}
                className={`w-full px-4 py-3 rounded-xl border text-sm focus:outline-none focus:ring-2 transition-all ${inputStyle}`}
              />

              <button
                onClick={step === "email" ? handleEmailLogin : handleRegister}
                disabled={authLoading || !email || !password}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 text-white font-medium text-sm hover:from-teal-400 hover:to-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                {authLoading
                  ? <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  : step === "email" ? <Lock size={13} /> : <UserPlus size={13} />
                }
                {authLoading ? "Please wait…" : step === "email" ? "Sign in" : "Create account"}
              </button>

              <div className="flex items-center justify-between pt-1">
                <button
                  onClick={() => { setStep(step === "email" ? "register" : "email"); setAuthError(""); }}
                  className={`text-[11px] transition-colors ${dark ? "text-teal-400 hover:text-teal-300" : "text-teal-600 hover:text-teal-700"}`}
                >
                  {step === "email" ? "Create account →" : "Already have an account →"}
                </button>
                <button onClick={() => { setStep("entry"); setAuthError(""); }} className={`flex items-center gap-1 text-[11px] transition-colors ${guestStyle}`}>
                  <ArrowLeft size={11} /> Back
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
