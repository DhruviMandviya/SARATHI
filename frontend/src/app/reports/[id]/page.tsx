"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();

  useEffect(() => {
    if (params.id) {
      router.replace(`/reports?appId=${params.id}`);
    }
  }, [params.id, router]);

  return (
    <div className="flex h-64 items-center justify-center text-xs text-slate-500 animate-pulse">
      Redirecting to Application Report Dossier...
    </div>
  );
}
