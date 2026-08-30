"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { api } from "@/lib/api";
import { formatEuros } from "@/core/finance";
import { eurosToCents } from "@/lib/money-input";
import { BottomSheet } from "@/components/BottomSheet";
import type { MonthListItem, CapitalDTO } from "@/lib/types";

export default function MoisPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const isAdmin = session?.user.role === "ADMIN";

  const [months, setMonths] = useState<MonthListItem[]>([]);
  const [capital, setCapital] = useState<CapitalDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [sheet, setSheet] = useState<"choice" | "addMonth" | "kharja" | "detail" | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, c] = await Promise.all([
        api.get<MonthListItem[]>("/api/months"),
        api.get<CapitalDTO>("/api/capital"),
      ]);
      setMonths(m);
      setCapital(c);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <div className="screen-header">
        <h1 className="screen-title">Mois</h1>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {isAdmin && (
            <button className="fab" aria-label="Ajouter" onClick={() => setSheet("choice")}>
              +
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="total-card">
        <div className="total-label">Total à moi (tous les mois)</div>
        <div className="total-value">{capital ? formatEuros(capital.total) : "—"}</div>
        <div className="row-between">
          <span />
          <button className="btn btn-sm btn-ghost" onClick={() => setSheet("detail")}>
            Détail
          </button>
        </div>
      </div>

      {months.map((m) => (
        <div key={m.id}>
          <div className="card card-tap" onClick={() => router.push(`/mois/${m.id}`)}>
            <div className="row-between">
              <span style={{ fontWeight: 700 }}>{m.label}</span>
              <span className={`amount-big ${m.remainder < 0 ? "amount-neg" : ""}`}>
                {formatEuros(m.remainder)}
              </span>
            </div>
          </div>
          {m.kharja && (
            <div className="kharja-band" onClick={() => router.push(`/mois/${m.id}/kharja`)}>
              Kharja : {formatEuros(m.kharja.net)}
            </div>
          )}
        </div>
      ))}

      {months.length === 0 && !error && (
        <p className="muted" style={{ textAlign: "center", marginTop: 24 }}>
          Aucun mois pour l'instant.
        </p>
      )}

      <div className="link-row" style={{ marginTop: 24 }}>
        <button className="btn btn-sm btn-ghost" onClick={() => signOut({ callbackUrl: "/login" })}>
          Déconnexion
        </button>
      </div>

      {sheet === "choice" && (
        <BottomSheet title="Ajouter" onClose={() => setSheet(null)}>
          <div className="sheet-list">
            <button className="btn btn-block" onClick={() => setSheet("addMonth")}>
              Ajouter un mois
            </button>
            <button
              className="btn btn-block"
              disabled={months.length === 0}
              onClick={() => setSheet("kharja")}
            >
              Kharja {months.length === 0 ? "(créez d'abord un mois)" : ""}
            </button>
          </div>
        </BottomSheet>
      )}

      {sheet === "addMonth" && (
        <AddMonthSheet
          onClose={() => setSheet(null)}
          onDone={async () => {
            setSheet(null);
            await load();
          }}
        />
      )}

      {sheet === "kharja" && (
        <KharjaChoiceSheet
          months={months}
          onClose={() => setSheet(null)}
          onPick={(monthId) => router.push(`/mois/${monthId}/kharja`)}
        />
      )}

      {sheet === "detail" && capital && (
        <BottomSheet title="Détail du capital" onClose={() => setSheet(null)}>
          <div className="sheet-list">
            {capital.breakdown.map((b) => (
              <div key={b.id} className="card" style={{ margin: 0 }}>
                <div style={{ fontWeight: 700, marginBottom: 4 }}>{b.label}</div>
                <div className="muted">
                  reste {formatEuros(b.remainder)} + Kharja net {formatEuros(b.kharjaNet)} ={" "}
                  <strong>{formatEuros(b.remainder + b.kharjaNet)}</strong>
                </div>
              </div>
            ))}
            <div className="row-between" style={{ padding: "8px 4px" }}>
              <strong>Total</strong>
              <strong>{formatEuros(capital.total)}</strong>
            </div>
          </div>
        </BottomSheet>
      )}
    </>
  );
}

function AddMonthSheet({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [label, setLabel] = useState("");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    const cents = eurosToCents(amount || "0");
    if (label.trim() === "" || cents === null) {
      setError("Nom et montant valides requis.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/api/months", { label: label.trim(), clientPayment: cents });
      onDone();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <BottomSheet title="Ajouter un mois" onClose={onClose}>
      <label className="field-label">Nom du mois</label>
      <input className="field" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Février 2026" />
      <label className="field-label">Revenu (payé par le client)</label>
      <input
        className="field"
        inputMode="decimal"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        placeholder="0,00"
      />
      {error && <div className="error-box" style={{ margin: "12px 0 0" }}>{error}</div>}
      <button className="btn btn-primary btn-block" style={{ marginTop: 20 }} onClick={save} disabled={busy}>
        Valider
      </button>
    </BottomSheet>
  );
}

function KharjaChoiceSheet({
  months,
  onClose,
  onPick,
}: {
  months: MonthListItem[];
  onClose: () => void;
  onPick: (monthId: string) => void;
}) {
  return (
    <BottomSheet title="Kharja — choisir le mois" onClose={onClose}>
      <div className="sheet-list">
        {months.map((m) => (
          <button key={m.id} className="btn btn-block" onClick={() => onPick(m.id)}>
            {m.label} {m.kharja ? "• existant" : ""}
          </button>
        ))}
      </div>
    </BottomSheet>
  );
}
