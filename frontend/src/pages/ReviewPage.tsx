import { useEffect, useState } from "react";
import {
  listResumes,
  updateResume,
  getCategoryStats,
  Resume,
  ResumeCategory,
  CategoryStats,
} from "../api/client";
import CandidateCard from "../components/CandidateCard";

type FilterValue = ResumeCategory | "sem_categoria" | "todos";

const FILTERS: { value: FilterValue; label: string }[] = [
  { value: "todos", label: "Todos" },
  { value: "otimo", label: "Ótimo" },
  { value: "bom", label: "Bom" },
  { value: "insuficiente", label: "Insuficiente" },
  { value: "sem_categoria", label: "Sem categoria" },
];

export default function ReviewPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [stats, setStats] = useState<CategoryStats | null>(null);
  const [filter, setFilter] = useState<FilterValue>("otimo");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [resumeData, statsData] = await Promise.all([
        listResumes({ category: filter === "todos" || filter === "sem_categoria" ? undefined : filter }),
        getCategoryStats(),
      ]);
      const finalList = filter === "sem_categoria" ? resumeData.filter((r) => !r.category) : resumeData;
      setResumes(finalList);
      setStats(statsData);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function handleCategorize(resume: Resume, category: ResumeCategory) {
    const next = resume.category === category ? null : category;
    const updated = await updateResume(resume.id, { category: next });
    applyUpdate(updated);
  }

  async function handleRate(resume: Resume, stars: number | null) {
    const updated = await updateResume(resume.id, { stars });
    applyUpdate(updated);
  }

  function applyUpdate(updated: Resume) {
    if (filter !== "todos" && updated.category !== filter) {
      setResumes((prev) => prev.filter((r) => r.id !== updated.id));
    } else {
      setResumes((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    }
    getCategoryStats().then(setStats).catch(() => undefined);
  }

  return (
    <div>
      <h1 className="page-title">Revisar currículos por categoria</h1>
      <p className="page-subtitle">Veja o resultado da categorização feita na tela anterior.</p>

      {stats && (
        <div className="stats-row">
          <div className="stat-card cat-total">
            <div className="stat-value">{stats.total}</div>
            <div className="stat-label">Total importado</div>
          </div>
          <div className="stat-card cat-otimo">
            <div className="stat-value">{stats.otimo}</div>
            <div className="stat-label">Ótimo</div>
          </div>
          <div className="stat-card cat-bom">
            <div className="stat-value">{stats.bom}</div>
            <div className="stat-label">Bom</div>
          </div>
          <div className="stat-card cat-insuficiente">
            <div className="stat-value">{stats.insuficiente}</div>
            <div className="stat-label">Insuficiente</div>
          </div>
        </div>
      )}

      <div className="tabs">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            className={`tab ${filter === f.value ? "active" : ""}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty-state">Carregando...</div>
      ) : resumes.length === 0 ? (
        <div className="empty-state">Nenhum currículo nessa categoria ainda.</div>
      ) : (
        <div className="card-list">
          {resumes.map((resume) => (
            <CandidateCard key={resume.id} resume={resume} onCategorize={handleCategorize} onRate={handleRate} />
          ))}
        </div>
      )}
    </div>
  );
}
