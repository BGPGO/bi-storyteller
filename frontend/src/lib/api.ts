const BASE = '/api/export';

export interface JobStatus {
  id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  total_steps: number;
  current_step: string;
  error?: string;
}

/** Export current page via screenshot from Screen Capture API */
export async function exportPage(
  screenshot: string,
  reportName: string,
  pageName = 'Página atual',
): Promise<Blob> {
  const res = await fetch(`${BASE}/page`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ screenshot, report_name: reportName, page_name: pageName }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'Erro ao gerar PDF');
  }

  return res.blob();
}

/** Start async full-report export via Playwright */
export async function startFullExport(url: string, reportName: string): Promise<string> {
  const res = await fetch(`${BASE}/full`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, report_name: reportName }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'Erro ao iniciar exportação');
  }

  const data = await res.json();
  return data.job_id as string;
}

/** Poll job status */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/status/${jobId}`);
  if (!res.ok) throw new Error('Job não encontrado');
  return res.json();
}

/** Download completed PDF */
export function getDownloadUrl(jobId: string): string {
  return `${BASE}/download/${jobId}`;
}

/** Download and return as Blob */
export async function downloadPdf(jobId: string): Promise<Blob> {
  const res = await fetch(getDownloadUrl(jobId));
  if (!res.ok) throw new Error('Erro ao baixar PDF');
  return res.blob();
}
