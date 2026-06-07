"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { useAuthStore } from "@/store/auth";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { AnimatedBg } from "@/components/animated-bg";
import { HealthWatchdog } from "@/components/health-watchdog";
import { ShareBadge } from "@/components/share-badge";

const PUBLIC_ROUTES = ["/"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session, status } = useSession();
  const zustandUser = useAuthStore((s) => s.user);
  const login = useAuthStore((s) => s.login);
  const isPublic = PUBLIC_ROUTES.includes(pathname);

  useEffect(() => {
    if (session?.user && !zustandUser) {
      login({
        name: session.user.name ?? session.user.email ?? "Google User",
        role: "operator",
        image: session.user.image ?? undefined,
        email: session.user.email ?? undefined,
      });
    }
  }, [session, zustandUser, login]);

  const isAuthenticated = !!zustandUser || !!session;
  const isLoading = status === "loading";

  useEffect(() => {
    if (!isPublic && !isLoading && !isAuthenticated) {
      router.replace("/");
    }
  }, [isPublic, isLoading, isAuthenticated, router]);

  if (isPublic) return <>{children}</>;
  if (isLoading || !isAuthenticated) return null;

  return (
    <div className="flex flex-col h-screen overflow-hidden text-slate-800 dark:text-slate-100 relative">
      <HealthWatchdog />
      <AnimatedBg />
      <div className="relative z-20 flex-shrink-0">
        <Header />
      </div>
      <div className="flex flex-1 overflow-hidden relative z-10">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
      <ShareBadge />
    </div>
  );
}
