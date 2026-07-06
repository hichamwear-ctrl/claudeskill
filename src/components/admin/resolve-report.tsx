"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ResolveReportButton({ reportId }: { reportId: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function resolve() {
    setLoading(true);
    const res = await fetch(`/api/admin/reports/${reportId}`, { method: "PATCH" });
    setLoading(false);
    if (res.ok) router.refresh();
  }

  return (
    <Button size="sm" variant="secondary" onClick={resolve} disabled={loading}>
      {loading ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
      Marquer résolu
    </Button>
  );
}
