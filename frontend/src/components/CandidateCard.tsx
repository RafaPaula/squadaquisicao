import { useState } from "react";
import { Resume, ResumeCategory, downloadResumeUrl, viewResumeUrl } from "../api/client";

const CATEGORY_LABEL: Record<ResumeCategory, string> = {
  insuficiente: "Insuficiente",
  bom: "Bom",
  otimo: "Ótimo",
};

export function CategoryBadge({ category }: { category: ResumeCategory | null }) {
  if (!category) return <span className="badge badge-none">Sem categoria</span>;
  return <span className={`badge badge-${category}`}>{CATEGORY_LABEL[category]}</span>;
}

function StarRating({
  stars,
  onSelect,
}: {
  stars: number | null;
  onSelect: (next: number | null) => void;
}) {
  return (
    <div className="star-rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className={`star-btn ${stars !== null && n <= stars ? "star-filled" : ""}`}
          onClick={() => onSelect(stars === n ? null : n)}
          title={`${n} estrela${n > 1 ? "s" : ""}`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

type Props = {
  resume: Resume;
  onCategorize: (resume: Resume, category: ResumeCategory) => void;
  onRate: (resume: Resume, stars: number | null) => void;
  defaultExpanded?: boolean;
};

export default function CandidateCard({ resume, onCategorize, onRate, defaultExpanded = false }: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="candidate-card">
      <div className="candidate-card-head" onClick={() => setExpanded((v) => !v)}>
        <div>
          <div className="candidate-name">{resume.candidate_name}</div>
          <div className="candidate-meta">
            {resume.candidate_email && <span>{resume.candidate_email}</span>}
            {resume.candidate_location && <span>{resume.candidate_location}</span>}
            <span>{new Date(resume.created_at).toLocaleDateString("pt-BR")}</span>
          </div>
        </div>
        <CategoryBadge category={resume.category} />
      </div>

      <div className="cat-buttons">
        {(Object.keys(CATEGORY_LABEL) as ResumeCategory[]).map((cat) => (
          <button
            key={cat}
            className={`cat-btn cat-btn-${cat} ${resume.category === cat ? "selected" : ""}`}
            onClick={() => onCategorize(resume, cat)}
          >
            {CATEGORY_LABEL[cat]}
          </button>
        ))}
        <StarRating stars={resume.stars} onSelect={(next) => onRate(resume, next)} />
      </div>

      {expanded && (
        <div className="candidate-detail">
          {resume.mime_type === "application/pdf" ? (
            <iframe
              className="candidate-detail-viewer"
              src={viewResumeUrl(resume.id)}
              title={`Currículo de ${resume.candidate_name}`}
            />
          ) : (
            <div className="candidate-detail-text">
              Visualização direta não disponível para este formato de arquivo
              ({resume.original_filename}).{" "}
              <a className="download-link" href={downloadResumeUrl(resume.id)} target="_blank" rel="noreferrer">
                Baixar para abrir
              </a>
              <hr />
              {resume.raw_text || "Texto do currículo não disponível."}
            </div>
          )}
          <div className="candidate-detail-side">
            <a className="download-link" href={downloadResumeUrl(resume.id)} target="_blank" rel="noreferrer">
              Baixar arquivo original
            </a>

            <div className="applied-jobs">
              <div className="applied-jobs-title">Vagas em que já se candidatou</div>
              {resume.applied_jobs && resume.applied_jobs.length > 0 ? (
                resume.applied_jobs.map((job) => (
                  <div key={job.id} className="applied-job-item">
                    <div className="applied-job-name">{job.name.trim()}</div>
                    <div className="applied-job-meta">
                      {job.stage && <span className="badge badge-none">{job.stage}</span>}
                      {job.status && <span className="applied-job-status">{job.status}</span>}
                    </div>
                  </div>
                ))
              ) : (
                <div className="candidate-meta">Nenhuma candidatura encontrada.</div>
              )}
            </div>

            {resume.tags && resume.tags.length > 0 && (
              <div className="candidate-meta">Tags: {resume.tags.join(", ")}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
