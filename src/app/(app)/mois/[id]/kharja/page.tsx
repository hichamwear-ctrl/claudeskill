"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { api } from "@/lib/api";
import { formatEuros } from "@/core/finance";
import { eurosToCents } from "@/lib/money-input";
import { BottomSheet } from "@/components/BottomSheet";
import type { KharjaDTO } from "@/lib/types";

export default function KharjaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { data: session } = useSession();
  const isAdmin = session?.user.role === "ADMIN";

  const [kharja, setKharja] = useState<KharjaDTO | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    try {
      const k = await api.get<KharjaDTO | null>(`/api/months/${id}/kharja`);
      setKharja(k);
      setLoaded(true);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function createKharja() {
    try {
      await api.post("/api/kharja", { monthId: id });
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const net = kharja?.lines.reduce((s, l) => s + (l.type === "IN" ? l.amount : -l.amount), 0) ?? 0;

  return (
    <>
      <div className="screen-header">
        <button className="back-btn" onClick={() => router.push("/")}>
          ‹ Mois
        </button>
        <span style={{ fontWeight: 700, color: "var(--kharja)" }}>Kharja</span>
        <span style={{ width: 40 }} />
      </div>

      {error && <div className="error-box">{error}</div>}

      {loaded && !kharja && (
        <div className="screen">
          <p className="muted">Aucun Kharja pour ce mois.</p>
          {isAdmin && (
            <button className="btn btn-primary btn-block" onClick={createKharja}>
              Créer le Kharja de ce mois
            </button>
          )}
        </div>
      )}

      {kharja && (
        <>
          <div className="total-card" style={{ background: "color-mix(in srgb, var(--kharja) 10%, white)" }}>
            <div className="total-label">Effet net sur le capital global</div>
            <div className="total-value" style={{ color: "var(--kharja)" }}>
              {formatEuros(net)}
            </div>
            <div className="muted">N'affecte jamais le reste du mois.</div>
          </div>

          {isAdmin && (
            <div style={{ margin: "0 16px 12px" }}>
              <button className="btn btn-block" onClick={() => setAdding(true)}>
                + Ajouter une ligne
              </button>
            </div>
          )}

          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            {kharja.lines.length === 0 && (
              <p className="muted" style={{ padding: 16, margin: 0 }}>
                Journal vide.
              </p>
            )}
            {kharja.lines.map((l) => {
              const signed = l.type === "IN" ? l.amount : -l.amount;
              return (
                <div className="hist-line" key={l.id} style={{ alignItems: "flex-start" }}>
                  <div className="hist-name">
                    <div style={{ fontWeight: 700 }}>{l.note || (l.type === "IN" ? "Entrée" : "Sortie")}</div>
                    <div className="muted">{new Date(l.createdAt).toLocaleDateString("fr-FR")}</div>
                  </div>
                  <span className={`hist-amount ${signed < 0 ? "amount-neg" : "amount-pos"}`}>
                    {formatEuros(signed)}
                  </span>
                  {isAdmin && (
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={async () => {
                        await api.del(`/api/kharja-lines/${l.id}`);
                        await load();
                      }}
                    >
                      🗑️
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}

      {adding && kharja && (
        <AddKharjaLineSheet
          kharjaId={kharja.id}
          onClose={() => setAdding(false)}
          onDone={async () => {
            setAdding(false);
            await load();
          }}
        />
      )}
    </>
  );
}

function AddKharjaLineSheet({
  kharjaId,
  onClose,
  onDone,
}: {
  kharjaId: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const [type, setType] = useState<"IN" | "OUT">("OUT");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    const cents = eurosToCents(amount);
    if (cents === null || cents <= 0) {
      setError("Montant invalide.");
      return;
    }
    setBusy(true);
    try {
      await api.post(`/api/kharja/${kharjaId}/lines`, { type, amount: cents, note: note.trim() });
      onDone();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <BottomSheet title="Ligne de Kharja" onClose={onClose}>
      <div className="seg">
        <button className={type === "OUT" ? "on" : ""} onClick={() => setType("OUT")}>
          Sortie (−)
        </button>
        <button className={type === "IN" ? "on" : ""} onClick={() => setType("IN")}>
          Entrée (+)
        </button>
      </div>
      <label className="field-label">Montant</label>
      <input className="field" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0,00" />
      <label className="field-label">Note</label>
      <input className="field" value={note} onChange={(e) => setNote(e.target.value)} placeholder="ex. prêt pour réparation voiture" />
      {error && <div className="error-box" style={{ margin: "12px 0 0" }}>{error}</div>}
      <button className="btn btn-primary btn-block" style={{ marginTop: 20 }} onClick={save} disabled={busy}>
        Valider
      </button>
    </BottomSheet>
  );
}
