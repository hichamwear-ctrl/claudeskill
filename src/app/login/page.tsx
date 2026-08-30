"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = await signIn("credentials", { email, password, redirect: false });
    setBusy(false);
    if (res?.error) {
      setError("Identifiants invalides ou compte temporairement verrouillé.");
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <div className="shell">
      <div className="screen" style={{ paddingTop: 64 }}>
        <h1 className="screen-title" style={{ marginBottom: 24 }}>
          Connexion
        </h1>
        <form onSubmit={submit}>
          <label className="field-label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            className="field"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <label className="field-label" htmlFor="password">
            Mot de passe
          </label>
          <input
            id="password"
            type="password"
            className="field"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <div className="error-box" style={{ margin: "16px 0 0" }}>{error}</div>}
          <button
            type="submit"
            className="btn btn-primary btn-block"
            style={{ marginTop: 24 }}
            disabled={busy}
          >
            {busy ? "Connexion…" : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
