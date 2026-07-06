"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Phone, PhoneOff, Send, Loader2, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: string;
  senderId: string;
  body: string;
  createdAt: string;
}

interface ActiveCall {
  id: string;
  note: string | null;
}

/**
 * Private order chat + audio call. Messages are polled (works without any
 * realtime backend); the call button drives the CallSession lifecycle. Both are
 * disabled once the conversation window closes (barber arrived / order done).
 */
export function OrderConversation({
  reservationId,
  currentUserId,
  active,
}: {
  reservationId: string;
  currentUserId: string;
  active: boolean;
}) {
  const { toast } = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [call, setCall] = useState<ActiveCall | null>(null);
  const sinceRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    const qs = sinceRef.current ? `?since=${encodeURIComponent(sinceRef.current)}` : "";
    const res = await fetch(`/api/reservations/${reservationId}/messages${qs}`);
    if (!res.ok) return;
    const { data } = await res.json();
    const incoming: ChatMessage[] = data?.messages ?? [];
    if (incoming.length) {
      sinceRef.current = incoming[incoming.length - 1].createdAt;
      setMessages((prev) => {
        const seen = new Set(prev.map((m) => m.id));
        return [...prev, ...incoming.filter((m) => !seen.has(m.id))];
      });
    }
  }, [reservationId]);

  // Initial load + polling every 3s.
  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function send() {
    const body = draft.trim();
    if (!body) return;
    setSending(true);
    const res = await fetch(`/api/reservations/${reservationId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    setSending(false);
    if (res.ok) {
      setDraft("");
      await load();
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Envoi impossible", description: error });
    }
  }

  async function startCall() {
    const res = await fetch(`/api/reservations/${reservationId}/call`, {
      method: "POST",
    });
    if (res.ok) {
      const { data } = await res.json();
      setCall({ id: data.call.id, note: data.note });
    } else {
      const { error } = await res.json().catch(() => ({ error: "Erreur" }));
      toast({ variant: "error", title: "Appel impossible", description: error });
    }
  }

  async function endCall() {
    if (!call) return;
    await fetch(`/api/reservations/${reservationId}/call`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ callId: call.id }),
    });
    setCall(null);
  }

  return (
    <div className="flex flex-col rounded-2xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <p className="text-sm font-semibold">Messagerie</p>
        {active ? (
          call ? (
            <Button size="sm" variant="destructive" onClick={endCall}>
              <PhoneOff className="size-4" /> Raccrocher
            </Button>
          ) : (
            <Button size="sm" variant="secondary" onClick={startCall}>
              <Phone className="size-4" /> Appeler
            </Button>
          )
        ) : (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Lock className="size-3" /> Conversation fermée
          </span>
        )}
      </div>

      {call && (
        <div className="flex items-center gap-2 border-b border-border bg-emerald-500/10 px-4 py-2 text-xs text-emerald-400">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400/60" />
            <span className="inline-flex size-2 rounded-full bg-emerald-400" />
          </span>
          En communication {call.note ? `— ${call.note}` : ""}
        </div>
      )}

      <div ref={scrollRef} className="max-h-72 min-h-40 space-y-2 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            {active
              ? "Démarrez la conversation."
              : "Aucun message pour cette commande."}
          </p>
        ) : (
          messages.map((m) => {
            const mine = m.senderId === currentUserId;
            return (
              <div
                key={m.id}
                className={cn("flex", mine ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "max-w-[75%] rounded-2xl px-3 py-2 text-sm",
                    mine
                      ? "bg-gold/20 text-foreground"
                      : "bg-secondary text-foreground",
                  )}
                >
                  {m.body}
                </div>
              </div>
            );
          })
        )}
      </div>

      {active && (
        <div className="flex items-center gap-2 border-t border-border p-3">
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Votre message…"
          />
          <Button size="icon" onClick={send} disabled={sending || !draft.trim()}>
            {sending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Send className="size-4" />
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
