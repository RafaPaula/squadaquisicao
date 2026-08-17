import { getStoredPassword } from "./auth";

export type ResumeCategory = "insuficiente" | "bom" | "otimo";

export type AppliedJob = {
  id: string;
  name: string;
  status: string | null;
  stage: string | null;
};

export type Resume = {
  id: number;
  inhire_resume_id: string;
  candidate_id: number;
  candidate_name: string;
  candidate_email: string | null;
  candidate_location: string | null;
  applied_jobs: AppliedJob[] | null;
  original_filename: string;
  mime_type: string | null;
  category: ResumeCategory | null;
  stars: number | null;
  tags: string[] | null;
  score: number | null;
  notes: string | null;
  raw_text: string | null;
  parsed_at: string | null;
  created_at: string;
};

export type CategoryStats = {
  insuficiente: number;
  bom: number;
  otimo: number;
  sem_categoria: number;
  total: number;
};

export const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const password = getStoredPassword();
  const headers = new Headers(init.headers);
  if (password) headers.set("X-App-Password", password);
  return fetch(`${BASE}${path}`, { ...init, headers });
}

/** Anexa a senha de acesso como query param, pra URLs navegadas direto
 * pelo navegador (iframe/download), que não carregam headers customizados. */
function withPasswordParam(url: string): string {
  const password = getStoredPassword();
  if (!password) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}pw=${encodeURIComponent(password)}`;
}

export async function listResumes(params: {
  q?: string;
  category?: string;
  min_score?: number;
  limit?: number;
}): Promise<Resume[]> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.category) search.set("category", params.category);
  if (params.min_score !== undefined) search.set("min_score", String(params.min_score));
  search.set("limit", String(params.limit ?? 250));

  const response = await apiFetch(`/resumes?${search.toString()}`);
  if (!response.ok) throw new Error(`Falha ao listar curriculos: ${response.status}`);
  return response.json();
}

export async function getCategoryStats(): Promise<CategoryStats> {
  const response = await apiFetch(`/resumes/stats/by-category`);
  if (!response.ok) throw new Error(`Falha ao buscar estatisticas: ${response.status}`);
  return response.json();
}

export async function updateResume(
  id: number,
  patch: Partial<Pick<Resume, "category" | "stars" | "tags" | "score" | "notes">>
): Promise<Resume> {
  const response = await apiFetch(`/resumes/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!response.ok) throw new Error(`Falha ao atualizar curriculo: ${response.status}`);
  return response.json();
}

export function downloadResumeUrl(id: number): string {
  return withPasswordParam(`${BASE}/resumes/${id}/download`);
}

export function viewResumeUrl(id: number): string {
  return withPasswordParam(`${BASE}/resumes/${id}/view`);
}

export async function triggerBackfill(limit = 200): Promise<unknown> {
  const response = await apiFetch(`/sync/backfill?limit=${limit}`, { method: "POST" });
  if (!response.ok) throw new Error(`Falha ao disparar backfill: ${response.status}`);
  return response.json();
}

export type FunnelJob = {
  id: number;
  title: string;
  stage: string;
  recruiter: string | null;
  recruiter_email: string | null;
  business_unit: string | null;
  area: string | null;
  hiring_manager: string | null;
  changed_at: string | null;
  created_at: string | null;
};

export type FunnelStats = {
  total: number;
  by_stage: { stage: string; count: number }[];
  by_recruiter: { recruiter: string; count: number }[];
  by_business_unit: { business_unit: string; count: number }[];
  by_area: { area: string; count: number }[];
};

export type Recruiter = { email: string; name: string };

export type JobComment = {
  id: number;
  text: string;
  author: string | null;
  created_at: string | null;
};

export async function listFunnelJobs(params: { recruiter?: string; stage?: string } = {}): Promise<FunnelJob[]> {
  const search = new URLSearchParams();
  if (params.recruiter) search.set("recruiter", params.recruiter);
  if (params.stage) search.set("stage", params.stage);
  const response = await apiFetch(`/jobs/funnel?${search.toString()}`);
  if (!response.ok) throw new Error(`Falha ao buscar funil de vagas: ${response.status}`);
  return response.json();
}

export async function getFunnelStats(): Promise<FunnelStats> {
  const response = await apiFetch(`/jobs/funnel/stats`);
  if (!response.ok) throw new Error(`Falha ao buscar estatisticas do funil: ${response.status}`);
  return response.json();
}

export async function listRecruiters(): Promise<Recruiter[]> {
  const response = await apiFetch(`/jobs/recruiters`);
  if (!response.ok) throw new Error(`Falha ao buscar recrutadoras: ${response.status}`);
  return response.json();
}

export async function updateFunnelJob(
  jobId: number,
  patch: { stage?: string; recruiter_email?: string }
): Promise<void> {
  const response = await apiFetch(`/jobs/funnel/${jobId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Falha ao atualizar vaga no Azure DevOps: ${detail || response.status}`);
  }
}

export async function listJobComments(jobId: number): Promise<JobComment[]> {
  const response = await apiFetch(`/jobs/funnel/${jobId}/comments`);
  if (!response.ok) throw new Error(`Falha ao buscar comentários: ${response.status}`);
  return response.json();
}

export async function addJobComment(jobId: number, text: string): Promise<JobComment> {
  const response = await apiFetch(`/jobs/funnel/${jobId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) throw new Error(`Falha ao adicionar comentário: ${response.status}`);
  return response.json();
}
