import { useEffect, useState } from "react";
import { listResumes, updateResume, triggerBackfill, Resume, ResumeCategory } from "../api/client";
import CandidateCard from "../components/CandidateCard";

export default function CategorizePage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [query, setQuery] = useState("");
  const [onlyUncategorized, setOnlyUncategorized] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(q?: string) {
    setLoading(true);
    try {
      const data = await listResumes({ q: q || undefined });
      setResumes(data);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    await load(query);
  }

  async function handleBackfill() {
    setSyncing(true);
    try {
      await triggerBackfill(200);
      await load(query);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSyncing(false);
    }
  }

  async function handleCategorize(resume: Resume, category: ResumeCategory) {
    const next = resume.category === category ? null : category;
    const updated = await updateResume(resume.id, { category: next });
    setResumes((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  }

  async function handleRate(resume: Resume, stars: number | null) {
    const updated = await updateResume(resume.id, { stars });
    setResumes((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  }

  const visible = onlyUncategorized ? resumes.filter((r) => !r.category) : resumes;

  return (
    <div>
      <h1 className="page-title">Categorizar currículos</h1>
      <p className="page-subtitle">
        Busque um candidato e classifique o currículo como Insuficiente, Bom ou Ótimo.
      </p>

      <form className="toolbar" onSubmit={handleSearch}>
        <input
          className="input input-search"
          placeholder="Buscar por nome, e-mail, telefone, vaga ou texto do currículo..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className="btn btn-primary" type="submit">
          Buscar
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => setOnlyUncategorized((v) => !v)}
        >
          {onlyUncategorized ? "Mostrando: só sem categoria" : "Mostrar só sem categoria"}
        </button>
        <button type="button" className="btn btn-ghost" onClick={handleBackfill} disabled={syncing}>
          {syncing ? "Sincronizando..." : "Importar últimos 200 da inHire"}
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty-state">Carregando...</div>
      ) : visible.length === 0 ? (
        <div className="empty-state">Nenhum currículo encontrado.</div>
      ) : (
        <div className="card-list">
          {visible.map((resume) => (
            <CandidateCard key={resume.id} resume={resume} onCategorize={handleCategorize} onRate={handleRate} />
          ))}
        </div>
      )}
    </div>
  );
}
