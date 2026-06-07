import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
import { NextAuthProvider } from "@/components/session-provider";
import { ThemeApplier } from "@/components/theme-applier";

export const metadata: Metadata = {
  title: "Eraya — Self-Healing Agent Swarm",
  description: "Operator console for the Eraya 4-archetype agent swarm framework",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      {/* Anti-FOUC: read persisted theme from localStorage before first paint */}
      <head>
        <script dangerouslySetInnerHTML={{ __html: `
          try {
            var t = JSON.parse(localStorage.getItem('eraya-theme') || '{}');
            if (t.state && t.state.dark) document.documentElement.classList.add('dark');
          } catch(e) {}
        ` }} />
      </head>
      <body>
        <NextAuthProvider>
          <ThemeApplier />
          <AppShell>{children}</AppShell>
        </NextAuthProvider>
      </body>
    </html>
  );
}
