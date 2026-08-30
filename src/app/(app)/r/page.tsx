"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { api } from "@/lib/api";
import { formatEuros, transferNet } from "@/core/finance";
import { eurosToCents } from "@/lib/money-input";
import { BottomSheet } from "@/components/BottomSheet";
import type { RDebtDTO } from "@/lib/types";

export default function RPage() {
  const { data: session } = useSession();
  const isAdmin = session?.user.role === "ADMIN";

  const [rdebt, setRdebt] = useState<RDebtDTO | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sheet, setSheet] = useState<"add" | "base" | null>(null);

  const load = useCallback(async () => {
    try {
      setRdebt(await api.get<RDebtDTO>("/api/rdebt"));
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
        <h1 className="screen-title">R</h1>
        {isAdmin && (
          <button className="fab" aria-label="Ajouter" onClick={() => setSheet("add")}>
            +
          </button>
        )}
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="total-card">
        <div className="total-label">Solde dû par R</div>
        <div className={`total-value ${rdebt && rdebt.balance < 0 ? "amount-neg" : ""}`}>
          {rdebt ? formatEuros(rdebt.balance) : "—"}
        </div>
        {isAdmin && rdebt && (
          <div className="row-between">
            <span className="muted">Base : {formatEuros(rdebt.baseAmount)}</span>
            <button className="btn btn-sm btn-ghost" onClick={() => setSheet("base")}>
              Modifier la base
            </button>
          </div>
        )}
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {rdebt?.lines.length === 0 && (
          <p className="muted" style={{ padding: 16, margin: 0 }}>
            Aucun mouvement.
          </p>
        )}
        {rdebt?.lines.map((l) => {
          const signed = l.type === "INCREASE" ? l.amountNet : -l.amountNet;
          const isTransfer = l.paymentMethod === "TRANSFER";
          return (
            <div className="hist-line" key={l.id} style={{ alignItems: "flex-start" }}>
              <div className="hist-name">
                <div style={{ fontWeight: 700 }}>
                  {l.type === "INCREASE" ? "Avance" : l.paymentMethod === "TRANSFER" ? "Remboursement (virement)" : "Remboursement (cash)"}
                </div>
                <div className="muted">{new Date(l.createdAt).toLocaleDateString("fr-FR")}</div>
                {isTransfer && (
                  <div className="muted">
                    Brut {formatEuros(l.amountGross)} → net {formatEuros(l.amountNet)} (−8 %)
                  </div>
                )}
              </div>
              <span className={`hist-amount ${signed < 0 ? "amount-neg" : "amount-pos"}`}>
                {formatEuros(signed)}
              </span>
              {isAdmin && (
                <button
                  className="btn btn-sm btn-ghost"
                  onClick={async () => {
                    await api.del(`/api/rdebt-lines/${l.id}`);
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

      {sheet === "add" && (
        <AddRLineSheet
          onClose={() => setSheet(null)}
          onDone={async () => {
            setSheet(null);
            await load();
          }}
        />
      )}

      {sheet === "base" && rdebt && (
        <BaseSheet
          initial={rdebt.baseAmount}
          onClose={() => setSheet(null)}
          onDone={async () => {
            setSheet(null);
            await load();
          }}
        />
      )}
    </>
  );
}

function AddRLineSheet({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [type, setType] = useState<"INCREASE" | "REPAYMENT">("REPAYMENT");
  const [method, setMethod] = useState<"CASH" | "TRANSFER">("CASH");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const cents = eurosToCents(amount);
  const previewNet =
    cents !== null && cents > 0 && type === "REPAYMENT" && method === "TRANSFER"
      ? transferNet(cents)
      : cents;

  async function save() {
    if (cents === null || cents <= 0) {
      setError("Montant invalide.");
      return;
    }
    setBusy(true);
    try {
      const payload =
        type === "REPAYMENT"
          ? { type, paymentMethod: method, amountGross: cents }
          : { type, amountGross: cents };
      await api.post("/api/rdebt/lines", payload);
      onDone();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <BottomSheet title="Mouvement R" onClose={onClose}>
      <div className="seg">
        <button className={type === "REPAYMENT" ? "on" : ""} onClick={() => setType("REPAYMENT")}>
          Remboursement (−)
        </button>
        <button className={type === "INCREASE" ? "on" : ""} onClick={() => setType("INCREASE")}>
          Avance (+)
        </button>
      </div>

      {type === "REPAYMENT" && (
        <>
          <label className="field-label">Mode</label>
          <div className="seg">
            <button className={method === "CASH" ? "on" : ""} onClick={() => setMethod("CASH")}>
              Cash
            </button>
            <button className={method === "TRANSFER" ? "on" : ""} onClick={() => setMethod("TRANSFER")}>
              Virement (−8 %)
            </button>
          </div>
        </>
      )}

      <label className="field-label">Montant {type === "REPAYMENT" && method === "TRANSFER" ? "(brut saisi)" : ""}</label>
      <input className="field" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0,00" />

      {type === "REPAYMENT" && method === "TRANSFER" && cents !== null && cents > 0 && (
        <div className="card" style={{ margin: "12px 0 0" }}>
          <div className="row-between">
            <span className="muted">Net réellement déduit</span>
            <strong>{formatEuros(previewNet ?? 0)}</strong>
          </div>
        </div>
      )}

      {error && <div className="error-box" style={{ margin: "12px 0 0" }}>{error}</div>}
      <button className="btn btn-primary btn-block" style={{ marginTop: 20 }} onClick={save} disabled={busy}>
        Valider
      </button>
    </BottomSheet>
  );
}

function BaseSheet({
  initial,
  onClose,
  onDone,
}: {
  initial: number;
  onClose: () => void;
  onDone: () => void;
}) {
  const [amount, setAmount] = useState((initial / 100).toFixed(2).replace(".", ","));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    const cents = eurosToCents(amount);
    if (cents === null) {
      setError("Montant invalide.");
      return;
    }
    setBusy(true);
    try {
      await api.patch("/api/rdebt", { baseAmount: cents });
      onDone();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <BottomSheet title="Montant de base" onClose={onClose}>
      <label className="field-label">Base due par R</label>
      <input className="field" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
      {error && <div className="error-box" style={{ margin: "12px 0 0" }}>{error}</div>}
      <button className="btn btn-primary btn-block" style={{ marginTop: 20 }} onClick={save} disabled={busy}>
        Enregistrer
      </button>
    </BottomSheet>
  );
}
