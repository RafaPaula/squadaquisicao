import { useEffect, useState } from "react";
import {
  FunnelJob,
  JobComment,
  Recruiter,
  addJobComment,
  listJobComments,
  updateFunnelJob,
} from "../api/client";

type Props = {
  job: FunnelJob;
  recruiters: Recruiter[];
  onClose: () => void;
  onChanged: (updated: Partial<FunnelJob>) => void;
};

export default function JobDetailModal({ job, recruiters, onClose, onChanged }: Props) {
  const [comments, setComments] = useState<JobComment[]>([]);
  const [loadingComments, setLoadingComments] = useState(true);
  const [newComment, setNewComment] = useState("");
  const [posting, setPosting] = useState(false);
  const [savingRecruiter, setSavingRecruiter] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listJobComments(job.id)
      .then(setComments)
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoadingComments(false));
  }, [job.id]);

  async function handleRecruiterChange(email: string) {
    setSavingRecruiter(true);
    try {
      await updateFunnelJob(job.id, { recruiter_email: email });
      const recruiter = recruiters.find((r) => r.email === email);
      onChanged({ recruiter_email: email, recruiter: recruiter?.name || null });
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSavingRecruiter(false);
    }
  }

  async function handleAddComment() {
    if (!newComment.trim()) return;
    setPosting(true);
    try {
      const comment = await addJobComment(job.id, newComment.trim());
      setComments((prev) => [...prev, comment]);
      setNewComment("");
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setPosting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-title">{job.title}</div>
            <div className="candidate-meta">
              {job.business_unit && <span>{job.business_unit}</span>}
              {job.area && <span>{job.area}</span>}
              <span>Etapa atual: {job.stage}</span>
            </div>
          </div>
          <button className="btn btn-ghost" onClick={onClose}>
            Fechar
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="modal-field">
          <label className="modal-label">Recrutadora responsável</label>
          <select
            className="select"
            value={job.recruiter_email || ""}
            onChange={(e) => handleRecruiterChange(e.target.value)}
            disabled={savingRecruiter}
          >
            <option value="">Sem responsável</option>
            {recruiters.map((r) => (
              <option key={r.email} value={r.email}>
                {r.name}
              </option>
            ))}
          </select>
          <p className="modal-hint">
            Alterar aqui atualiza direto o campo "Assigned To" no work item do Azure DevOps.
          </p>
        </div>

        <div className="modal-field">
          <label className="modal-label">Comentários (Discussion no Azure DevOps)</label>
          <div className="comment-list">
            {loadingComments ? (
              <div className="candidate-meta">Carregando...</div>
            ) : comments.length === 0 ? (
              <div className="candidate-meta">Nenhum comentário ainda.</div>
            ) : (
              comments.map((c) => (
                <div key={c.id} className="comment-item">
                  <div className="comment-meta">
                    <strong>{c.author || "Alguém"}</strong>
                    {c.created_at && <span> · {new Date(c.created_at).toLocaleString("pt-BR")}</span>}
                  </div>
                  <div
                    className="comment-text"
                    // O Azure DevOps guarda comentarios como HTML simples.
                    dangerouslySetInnerHTML={{ __html: c.text }}
                  />
                </div>
              ))
            )}
          </div>
          <textarea
            className="input comment-input"
            placeholder="Escrever um comentário..."
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            rows={3}
          />
          <button className="btn btn-primary" onClick={handleAddComment} disabled={posting || !newComment.trim()}>
            {posting ? "Enviando..." : "Adicionar comentário"}
          </button>
        </div>
      </div>
    </div>
  );
}
