"use client";
export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-base font-semibold mb-1">Settings</h1>
      <p className="text-xs text-slate-500 mb-6">Eraya operator console configuration</p>

      <div className="rounded-xl border border-[#1f2937] bg-[#111827] p-5 space-y-4">
        <Setting label="API URL" value={process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"} />
        <Setting label="WebSocket URL" value={process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000"} />
        <Setting label="Version" value="0.1.0 — Microsoft Build 2026" />
        <Setting label="Framework" value="Eraya — Self-Healing Agent Swarm" />
      </div>
    </div>
  );
}

function Setting({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#1f2937] last:border-0">
      <span className="text-sm text-slate-400">{label}</span>
      <span className="text-xs font-mono text-slate-300">{value}</span>
    </div>
  );
}
