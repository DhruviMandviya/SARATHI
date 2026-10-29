"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.push("/login");
      } else {
        router.push("/dashboard");
      }
    }
  }, [user, isLoading, router]);

  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="animate-pulse text-sm text-slate-500 font-medium">
        Loading SARATHI Regulatory Governance Platform...
      </div>
    </div>
  );
}
