import { useEffect, useMemo, useState } from "react";
import {
  FunnelJob,
  FunnelStats,
  Recruiter,
  getFunnelStats,
  listFunnelJobs,
  listRecruiters,
  updateFunnelJob,
} from "../api/client";
import JobDetailModal from "../components/JobDetailModal";

const STAGE_ORDER = [
  "Backlog",
  "Abertura da Vaga",
  "Triagem/Hunting",
  "Entrevista Inicial",
  "Entrevista Gestor",
  "Entrevista Técnica/Time",
  "Diligência",
  "Fechamento",
  "Impedimento",
  "Cancelada",
  "Contratada",
];

const STAGE_STYLE: Record<string, string> = {
  Backlog: "column-neutral",
  "Abertura da Vaga": "column-neutral",
  "Triagem/Hunting": "column-progress",
  "Entrevista Inicial": "column-progress",
  "Entrevista Gestor": "column-progress",
  "Entrevista Técnica/Time": "column-progress",
  "Diligência": "column-progress",
  Fechamento: "column-progress",
  Impedimento: "column-warning",
  Cancelada: "column-danger",
  Contratada: "column-success",
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase();
}

export default function FunnelPage() {
  const [jobs, setJobs] = useState<FunnelJob[]>([]);
  const [stats, setStats] = useState<FunnelStats | null>(null);
  const [recruiters, setRecruiters] = useState<Recruiter[]>([]);
  const [recruiterFilter, setRecruiterFilter] = useState<string>("");
  const [businessUnitFilter, setBusinessUnitFilter] = useState<string>("");
  const [areaFilter, setAreaFilter] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragJobId, setDragJobId] = useState<number | null>(null);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<FunnelJob | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [jobsData, statsData, recruitersData] = await Promise.all([
        listFunnelJobs({}),
        getFunnelStats(),
        listRecruiters(),
      ]);
      setJobs(jobsData);
      setStats(statsData);
      setRecruiters(recruitersData);
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

  const columns = useMemo(() => {
    const filtered = jobs.filter((j) => {
      if (recruiterFilter && (j.recruiter || "Sem responsável") !== recruiterFilter) return false;
      if (businessUnitFilter && (j.business_unit || "Sem unidade de negócio") !== businessUnitFilter)
        return false;
      if (areaFilter && (j.area || "Sem área") !== areaFilter) return false;
      return true;
    });
    const anyFilterActive = Boolean(recruiterFilter || businessUnitFilter || areaFilter);

    return STAGE_ORDER.map((stage) => ({
      stage,
      jobs: filtered.filter((j) => j.stage === stage),
    })).filter((col) => col.jobs.length > 0 || !anyFilterActive);
  }, [jobs, recruiterFilter, businessUnitFilter, areaFilter]);

  function patchJobLocally(jobId: number, patch: Partial<FunnelJob>) {
    setJobs((prev) => prev.map((j) => (j.id === jobId ? { ...j, ...patch } : j)));
    setSelectedJob((prev) => (prev && prev.id === jobId ? { ...prev, ...patch } : prev));
  }

  async function handleDrop(stage: string) {
    setDragOverStage(null);
    const jobId = dragJobId;
    setDragJobId(null);
    if (jobId === null) return;

    const job = jobs.find((j) => j.id === jobId);
    if (!job || job.stage === stage) return;

    const previousStage = job.stage;
    patchJobLocally(jobId, { stage }); // otimista
    try {
      await updateFunnelJob(jobId, { stage });
      getFunnelStats().then(setStats).catch(() => undefined);
    } catch (err) {
      patchJobLocally(jobId, { stage: previousStage }); // reverte
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <h1 className="page-title">Funil de Vagas</h1>
      <p className="page-subtitle">
        Espelho de mão dupla com o board de Aquisição de Talentos no Azure DevOps — arraste um
        card pra mudar a etapa, clique para reatribuir a recrutadora ou comentar.
      </p>

      <div className="toolbar">
        <select
          className="select"
          value={recruiterFilter}
          onChange={(e) => setRecruiterFilter(e.target.value)}
        >
          <option value="">Todas as recrutadoras</option>
          {stats?.by_recruiter.map((r) => (
            <option key={r.recruiter} value={r.recruiter}>
              {r.recruiter} ({r.count})
            </option>
          ))}
        </select>
        <select
          className="select"
          value={businessUnitFilter}
          onChange={(e) => setBusinessUnitFilter(e.target.value)}
        >
          <option value="">Todas as unidades de negócio</option>
          {stats?.by_business_unit.map((b) => (
            <option key={b.business_unit} value={b.business_unit}>
              {b.business_unit} ({b.count})
            </option>
          ))}
        </select>
        <select className="select" value={areaFilter} onChange={(e) => setAreaFilter(e.target.value)}>
          <option value="">Todas as áreas</option>
          {stats?.by_area.map((a) => (
            <option key={a.area} value={a.area}>
              {a.area} ({a.count})
            </option>
          ))}
        </select>
        {stats && <span className="candidate-meta">{stats.total} vagas no total</span>}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty-state">Carregando...</div>
      ) : (
        <div className="kanban-board">
          {columns.map((col) => (
            <div
              key={col.stage}
              className={`kanban-column ${STAGE_STYLE[col.stage] || "column-neutral"} ${
                dragOverStage === col.stage ? "drag-over" : ""
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOverStage(col.stage);
              }}
              onDragLeave={() => setDragOverStage((prev) => (prev === col.stage ? null : prev))}
              onDrop={() => handleDrop(col.stage)}
            >
              <div className="kanban-column-header">
                <span>{col.stage}</span>
                <span className="kanban-column-count">{col.jobs.length}</span>
              </div>
              <div className="kanban-column-body">
                {col.jobs.map((job) => (
                  <div
                    key={job.id}
                    className="kanban-card"
                    draggable
                    onDragStart={() => setDragJobId(job.id)}
                    onDragEnd={() => setDragJobId(null)}
                    onClick={() => setSelectedJob(job)}
                  >
                    <div className="kanban-card-title">{job.title}</div>
                    <div className="kanban-card-meta">
                      {job.business_unit && <span className="kanban-tag">{job.business_unit}</span>}
                      {job.area && <span className="kanban-tag">{job.area}</span>}
                    </div>
                    <div className="kanban-card-footer">
                      {job.recruiter ? (
                        <span className="kanban-avatar" title={job.recruiter}>
                          {initials(job.recruiter)}
                        </span>
                      ) : (
                        <span className="kanban-avatar kanban-avatar-empty">?</span>
                      )}
                      <span className="kanban-recruiter-name">
                        {job.recruiter || "Sem responsável"}
                      </span>
                    </div>
                  </div>
                ))}
                {col.jobs.length === 0 && <div className="kanban-column-empty">Vazio</div>}
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedJob && (
        <JobDetailModal
          job={selectedJob}
          recruiters={recruiters}
          onClose={() => setSelectedJob(null)}
          onChanged={(patch) => patchJobLocally(selectedJob.id, patch)}
        />
      )}
    </div>
  );
}
