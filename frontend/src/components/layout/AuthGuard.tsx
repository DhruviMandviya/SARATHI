"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading } = useAuth();

  const isPublicRoute = pathname === "/login";

  const officialOnlyPrefixes = ["/verification", "/fraud", "/compliance", "/audit", "/admin"];

  useEffect(() => {
    if (!isLoading) {
      if (!user && !isPublicRoute) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("aicte_token");
          window.location.href = "/login";
        }
      } else if (user && isPublicRoute) {
        router.replace("/dashboard");
      } else if (user && user.role === "institution") {
        if (officialOnlyPrefixes.some((prefix) => pathname.startsWith(prefix))) {
          router.replace("/dashboard");
        }
      }
    }
  }, [user, isLoading, isPublicRoute, pathname, router]);

  if (isLoading && !isPublicRoute) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[#0A4D2E] border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold text-slate-600">Verifying council credentials...</p>
        </div>
      </div>
    );
  }

  if (!user && !isPublicRoute) {
    return null;
  }

  if (isPublicRoute) {
    return <main className="min-h-screen bg-slate-50">{children}</main>;
  }

  return <>{children}</>;
}
