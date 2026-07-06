"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";

export function AdminNoteForm({ barberId }: { barberId: string }) {
  const router = useRouter();
  const { toast } = useToast();
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(false);

  async function add() {
    if (!body.trim()) return;
    setLoading(true);
    const res = await fetch("/api/admin/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ barberId, body }),
    });
    setLoading(false);
    if (res.ok) {
      setBody("");
      router.refresh();
    } else {
      toast({ variant: "error", title: "Note non enregistrée" });
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Input
        value={body}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && add()}
        placeholder="Ajouter une note interne…"
        className="h-9"
      />
      <Button size="sm" onClick={add} disabled={loading || !body.trim()}>
        {loading ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
      </Button>
    </div>
  );
}
