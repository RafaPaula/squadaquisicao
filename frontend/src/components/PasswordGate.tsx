import { FormEvent, ReactNode, useEffect, useState } from "react";
import { BASE } from "../api/client";
import { checkPassword, getStoredPassword, setStoredPassword } from "../api/auth";

type Status = "checking" | "locked" | "unlocked";

export default function PasswordGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("checking");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    checkPassword(BASE, getStoredPassword())
      .then((ok) => setStatus(ok ? "unlocked" : "locked"))
      .catch(() => setStatus("locked"));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const ok = await checkPassword(BASE, password);
      if (ok) {
        setStoredPassword(password);
        setStatus("unlocked");
      } else {
        setError("Senha incorreta.");
      }
    } catch {
      setError("Não foi possível verificar a senha. Tente novamente.");
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "checking") {
    return <div className="empty-state">Carregando...</div>;
  }

  if (status === "locked") {
    return (
      <div className="password-gate">
        <form className="password-gate-form" onSubmit={handleSubmit}>
          <h1 className="page-title">Talent Mirror</h1>
          <p className="page-subtitle">Digite a senha de acesso para continuar.</p>
          <input
            className="input"
            type="password"
            autoFocus
            placeholder="Senha de acesso"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <div className="error-banner">{error}</div>}
          <button className="btn btn-primary" type="submit" disabled={submitting || !password}>
            {submitting ? "Verificando..." : "Entrar"}
          </button>
        </form>
      </div>
    );
  }

  return <>{children}</>;
}
