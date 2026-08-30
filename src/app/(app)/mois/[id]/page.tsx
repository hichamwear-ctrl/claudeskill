"use client";

import { use, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { api } from "@/lib/api";
import { formatEuros, vat, recoveredVat } from "@/core/finance";
import { eurosToCents } from "@/lib/money-input";
import { BottomSheet } from "@/components/BottomSheet";
import { Icon, ICON_CHOICES } from "@/components/Icon";
import type { CategoryDTO, ExpenseLineDTO, MonthDetail } from "@/lib/types";
import { RECOVERED_VAT_ALLOWED_NAMES } from "@/lib/categories";

export default function MonthDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { data: session } = useSession();
  const isAdmin = session?.user.role === "ADMIN";

  const [month, setMonth] = useState<MonthDetail | null>(null);
  const [categories, setCategories] = useState<CategoryDTO[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<
    | { kind: "category"; category: CategoryDTO }
    | { kind: "addCategory" }
    | { kind: "vat" }
    | { kind: "recoveredVat" }
    | { kind: "editRevenue" }
    | { kind: "editLine"; line: ExpenseLineDTO }
    | null
  >(null);

  const load = useCallback(async () => {
    try {
      const [m, c] = await Promise.all([
        api.get<MonthDetail>(`/api/months/${id}`),
        api.get<CategoryDTO[]>("/api/categories"),
      ]);
      setMonth(m);
      setCategories(c);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <div className="error-box">{error}</div>;
  if (!month) return <p className="muted screen">Chargement…</p>;

  const subtractions = categories.filter((c) => c.type === "SUBTRACTION");
  const additions = categories.filter((c) => c.type === "ADDITION");

  return (
    <>
      <div className="screen-header">
        <button className="back-btn" onClick={() => router.push("/")}>
          ‹ Mois
        </button>
        <span style={{ fontWeight: 700 }}>{month.label}</span>
        <span style={{ width: 40 }} />
      </div>

      <div className="total-card">
        <div className="row-between">
          <div>
            <div className="total-label">Revenu</div>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{formatEuros(month.clientPayment)}</div>
          </div>
          {isAdmin && (
            <button className="btn btn-sm" onClick={() => setActive({ kind: "editRevenue" })}>
              Modifier
            </button>
          )}
        </div>
        <div style={{ marginTop: 14 }}>
          <div className="total-label">Reste net du mois</div>
          <div className={`total-value ${month.remainder < 0 ? "amount-neg" : ""}`}>
            {formatEuros(month.remainder)}
          </div>
        </div>
      </div>

      {/* Historique */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {month.expenses.length === 0 && (
          <p className="muted" style={{ padding: 16, margin: 0 }}>
            Aucune ligne.
          </p>
        )}
        {month.expenses.map((line) => {
          const signed = line.category.type === "ADDITION" ? line.amount : -line.amount;
          return (
            <div className="hist-line" key={line.id}>
              <Icon name={line.category.icon} />
              <span className="hist-name">{line.category.name}</span>
              <span className={`hist-amount ${signed < 0 ? "amount-neg" : "amount-pos"}`}>
                {formatEuros(signed)}
              </span>
              {isAdmin && (
                <span style={{ display: "flex", gap: 6 }}>
                  {!line.category.isSystem && (
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={() => setActive({ kind: "editLine", line })}
                    >
                      ✏️
                    </button>
                  )}
                  <button
                    className="btn btn-sm btn-ghost"
                    onClick={async () => {
                      await api.del(`/api/lines/${line.id}`);
                      await load();
                    }}
                  >
                    🗑️
                  </button>
                </span>
              )}
            </div>
          );
        })}
      </div>

      {isAdmin && (
        <>
          {/* Actions de calcul */}
          <div style={{ display: "flex", gap: 10, margin: "12px 16px" }}>
            <button className="btn btn-block" onClick={() => setActive({ kind: "vat" })}>
              TVA
            </button>
            <button className="btn btn-block" onClick={() => setActive({ kind: "recoveredVat" })}>
              Récupérer TVA
            </button>
          </div>

          <div className="muted" style={{ margin: "16px 16px 4px", fontWeight: 700 }}>
            Dépenses (−)
          </div>
          <div className="cat-grid">
            {subtractions.map((c) => (
              <button key={c.id} className="cat-btn" onClick={() => setActive({ kind: "category", category: c })}>
                <span className="cat-icon">
                  <Icon name={c.icon} />
                </span>
                {c.name}
              </button>
            ))}
          </div>

          <div className="muted" style={{ margin: "8px 16px 4px", fontWeight: 700 }}>
            Additions (+)
          </div>
          <div className="cat-grid">
            {additions.map((c) => (
              <button key={c.id} className="cat-btn" onClick={() => setActive({ kind: "category", category: c })}>
                <span className="cat-icon">
                  <Icon name={c.icon} />
                </span>
                {c.name}
              </button>
            ))}
            <button className="cat-btn" onClick={() => setActive({ kind: "addCategory" })}>
              <span className="cat-icon">➕</span>
              Ajouter une catégorie
            </button>
          </div>
        </>
      )}

      <div style={{ margin: "16px" }}>
        <a className="btn btn-block" href={`/api/months/${id}/pdf`} target="_blank" rel="noreferrer">
          Voir détail (PDF)
        </a>
      </div>

      {active?.kind === "category" && (
        <AmountSheet
          title={active.category.name}
          onClose={() => setActive(null)}
          onSubmit={async (cents) => {
            await api.post(`/api/months/${id}/lines`, { categoryId: active.category.id, amount: cents });
            setActive(null);
            await load();
          }}
        />
      )}

      {active?.kind === "editRevenue" && (
        <AmountSheet
          title="Modifier le revenu"
          initial={month.clientPayment}
          allowZero
          onClose={() => setActive(null)}
          onSubmit={async (cents) => {
            await api.patch(`/api/months/${id}`, { clientPayment: cents });
            setActive(null);
            await load();
          }}
        />
      )}

      {active?.kind === "editLine" && (
        <AmountSheet
          title={`Modifier ${active.line.category.name}`}
          initial={active.line.amount}
          onClose={() => setActive(null)}
          onSubmit={async (cents) => {
            await api.patch(`/api/lines/${active.line.id}`, { amount: cents });
            setActive(null);
            await load();
          }}
        />
      )}

      {active?.kind === "addCategory" && (
        <AddCategorySheet
          onClose={() => setActive(null)}
          onDone={async () => {
            setActive(null);
            await load();
          }}
        />
      )}

      {active?.kind === "vat" && (
        <VatSheet
          month={month}
          mode="vat"
          onClose={() => setActive(null)}
          onDone={async () => {
            setActive(null);
            await load();
          }}
        />
      )}

      {active?.kind === "recoveredVat" && (
        <VatSheet
          month={month}
          mode="recoveredVat"
          onClose={() => setActive(null)}
          onDone={async () => {
            setActive(null);
            await load();
          }}
        />
      )}
    </>
  );
}

function AmountSheet({
  title,
  initial,
  allowZero,
  onClose,
  onSubmit,
}: {
  title: string;
  initial?: number;
  allowZero?: boolean;
  onClose: () => void;
  onSubmit: (cents: number) => Promise<void>;
}) {
  const [value, setValue] = useState(initial !== undefined ? (initial / 100).toFixed(2).replace(".", ",") : "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    const cents = eurosToCents(value);
    if (cents === null || (!allowZero && cents <= 0)) {
      setError("Montant invalide.");
      return;
    }
    setBusy(true);
    try {
      await onSubmit(cents);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <BottomSheet title={title} onClose={onClose}>
      <label className="field-label">Montant</label>
      <input
        className="field"
        inputMode="decimal"
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="0,00"
      />
      {error && <div className="error-box" style={{ margin: "12px 0 0" }}>{error}</div>}
      <button className="btn btn-primary btn-block" style={{ marginTop: 20 }} onClick={submit} disabled={busy}>
        Valider
      </button>
    </BottomSheet>
  );
}

function AddCategorySheet({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [name, setName] = useState("");
  const [icon, setIcon] = useState(ICON_CHOICES[0] ?? "tag");
  const [type, setType] = useState<"SUBTRACTION" | "ADDITION">("SUBTRACTION");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    if (name.trim() === "") {
      setError("Nom requis.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/api/categories", { name: name.trim(), icon, type });
      onDone();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <BottomSheet title="Nouvelle catégorie" onClose={onClose}>
      <label className="field-label">Nom</label>
      <input className="field" value={name} onChange={(e) => setName(e.target.value)} />
      <label className="field-label">Type</label>
      <div className="seg">
        <button className={type === "SUBTRACTION" ? "on" : ""} onClick={() => setType("SUBTRACTION")}>
          Soustraction (−)
        </button>
        <button className={type === "ADDITION" ? "on" : ""} onClick={() => setType("ADDITION")}>
          Addition (+)
        </button>
      </div>
      <label className="field-label">Icône</label>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {ICON_CHOICES.map((k) => (
          <button
            key={k}
            className="cat-btn"
            style={{ width: 56, minHeight: 56, border: icon === k ? "2px solid var(--accent)" : undefined }}
            onClick={() => setIcon(k)}
          >
            <Icon name={k} />
          </button>
        ))}
      </div>
      {error && <div className="error-box" style={{ margin: "12px 0 0" }}>{error}</div>}
      <button className="btn btn-primary btn-block" style={{ marginTop: 20 }} onClick={save} disabled={busy}>
        Créer
      </button>
    </BottomSheet>
  );
}

function VatSheet({
  month,
  mode,
  onClose,
  onDone,
}: {
  month: MonthDetail;
  mode: "vat" | "recoveredVat";
  onClose: () => void;
  onDone: () => void;
}) {
  const isRecovery = mode === "recoveredVat";
  // Récupérer TVA : uniquement Essence / Location Camionnette, jamais le revenu.
  const eligibleLines = month.expenses.filter((l) =>
    isRecovery
      ? RECOVERED_VAT_ALLOWED_NAMES.includes(l.category.name as never)
      : !l.category.isSystem,
  );

  const [includeRevenue, setIncludeRevenue] = useState(false);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selected: number[] = [];
  if (!isRecovery && includeRevenue) selected.push(month.clientPayment);
  for (const l of eligibleLines) if (checked[l.id]) selected.push(l.amount);

  const preview = selected.length > 0 ? (isRecovery ? recoveredVat(selected) : vat(selected)) : 0;
  const total = selected.reduce((s, v) => s + v, 0);

  async function save() {
    if (selected.length === 0) {
      setError("Sélectionnez au moins un élément.");
      return;
    }
    setBusy(true);
    try {
      const lineIds = eligibleLines.filter((l) => checked[l.id]).map((l) => l.id);
      const url = isRecovery
        ? `/api/months/${month.id}/recovered-vat`
        : `/api/months/${month.id}/vat`;
      await api.post(url, { includeRevenue: isRecovery ? false : includeRevenue, lineIds });
      onDone();
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <BottomSheet title={isRecovery ? "Récupérer TVA" : "TVA"} onClose={onClose}>
      {!isRecovery && (
        <label className="check-row">
          <input
            type="checkbox"
            checked={includeRevenue}
            onChange={(e) => setIncludeRevenue(e.target.checked)}
          />
          <span className="hist-name">Revenu</span>
          <span>{formatEuros(month.clientPayment)}</span>
        </label>
      )}
      {eligibleLines.map((l) => (
        <label className="check-row" key={l.id}>
          <input
            type="checkbox"
            checked={!!checked[l.id]}
            onChange={(e) => setChecked((p) => ({ ...p, [l.id]: e.target.checked }))}
          />
          <span className="hist-name">{l.category.name}</span>
          <span>{formatEuros(l.amount)}</span>
        </label>
      ))}
      {isRecovery && eligibleLines.length === 0 && (
        <p className="muted">Aucune dépense éligible (Essence, Location Camionnette).</p>
      )}

      <div className="card" style={{ margin: "16px 0 0" }}>
        <div className="row-between">
          <span className="muted">Somme sélectionnée</span>
          <strong>{formatEuros(total)}</strong>
        </div>
        <div className="row-between" style={{ marginTop: 6 }}>
          <span className="muted">{isRecovery ? "TVA récupérée" : "TVA à déduire"}</span>
          <strong>{formatEuros(preview)}</strong>
        </div>
      </div>

      {error && <div className="error-box" style={{ margin: "12px 0 0" }}>{error}</div>}
      <button className="btn btn-primary btn-block" style={{ marginTop: 20 }} onClick={save} disabled={busy}>
        {isRecovery ? "Enregistrer la TVA récupérée" : "Déduire la TVA"}
      </button>
    </BottomSheet>
  );
}
