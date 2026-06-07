"use client";
import { useState } from "react";
import { Share2, Copy, Check, Mail, Bot, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function ShareBadge() {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  function copyLink() {
    navigator.clipboard.writeText(window.location.origin).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-2">

      {/* Expanded card */}
      {open && (
        <div className="w-64 rounded-2xl border border-teal-200 dark:border-teal-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md shadow-2xl shadow-teal-900/20 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-teal-500 to-cyan-500 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bot size={14} className="text-white" />
              <span className="text-white text-xs font-bold tracking-wide">Eraya · Agent Swarm</span>
            </div>
            <button onClick={() => setOpen(false)} className="text-white/70 hover:text-white transition-colors">
              <X size={13} />
            </button>
          </div>

          {/* Body */}
          <div className="px-4 py-3 space-y-3">
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              A self-healing AI agent swarm for 5G, Cloud, ICU and Network domains.
              Built for <span className="font-semibold text-teal-600 dark:text-teal-400">Microsoft Build AI Hackathon 2026</span>.
            </p>

            {/* Creator */}
            <div className="flex items-center gap-2 py-2 border-t border-slate-100 dark:border-slate-800">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-orange-400 to-teal-400 flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0">
                PS
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-200">Pardeep Sandhu</div>
                <a
                  href="mailto:sandhupardeep300@gmail.com"
                  className="text-[10px] text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1"
                >
                  <Mail size={9} /> sandhupardeep300@gmail.com
                </a>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={copyLink}
                className={cn(
                  "flex-1 flex items-center justify-center gap-1.5 text-[11px] font-medium py-2 rounded-xl border transition-all",
                  copied
                    ? "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400"
                    : "bg-teal-50 dark:bg-teal-900/20 border-teal-200 dark:border-teal-800 text-teal-600 dark:text-teal-400 hover:bg-teal-100 dark:hover:bg-teal-900/40"
                )}
              >
                {copied ? <><Check size={11} /> Copied!</> : <><Copy size={11} /> Copy link</>}
              </button>
              <a
                href="mailto:sandhupardeep300@gmail.com?subject=Eraya - AI Agent Swarm"
                className="flex items-center justify-center gap-1.5 text-[11px] font-medium py-2 px-3 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-teal-200 dark:hover:border-teal-800 hover:text-teal-600 transition-all"
              >
                <Mail size={11} />
              </a>
            </div>

            <p className="text-[10px] text-slate-400 dark:text-slate-600 text-center">
              Love chatbots & AI agents? Let&apos;s connect ↑
            </p>
          </div>
        </div>
      )}

      {/* Toggle button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex items-center gap-2 pl-3 pr-4 py-2.5 rounded-full shadow-lg shadow-teal-900/20 transition-all duration-200 font-medium text-xs",
          open
            ? "bg-slate-800 dark:bg-slate-700 text-white"
            : "bg-gradient-to-r from-teal-500 to-cyan-500 text-white hover:from-teal-400 hover:to-cyan-400"
        )}
      >
        <Share2 size={13} />
        <span>{open ? "Close" : "Share · Contact"}</span>
      </button>
    </div>
  );
}
