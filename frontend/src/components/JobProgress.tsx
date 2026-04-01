import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Loader2, Download } from 'lucide-react';
import { getJobStatus, downloadPdf, type JobStatus } from '../lib/api';

interface Props {
  jobId: string;
  reportName: string;
  onDone: (pdfBlob: Blob) => void;
  onError: (msg: string) => void;
}

const POLL_INTERVAL_MS = 2000;

export default function JobProgress({ jobId, reportName, onDone, onError }: Props) {
  const [status, setStatus] = useState<JobStatus | null>(null);

  useEffect(() => {
    let stopped = false;

    const poll = async () => {
      while (!stopped) {
        try {
          const s = await getJobStatus(jobId);
          setStatus(s);

          if (s.status === 'completed') {
            const blob = await downloadPdf(jobId);
            onDone(blob);
            return;
          }

          if (s.status === 'failed') {
            onError(s.error ?? 'Erro desconhecido no processamento');
            return;
          }
        } catch (e) {
          onError(e instanceof Error ? e.message : 'Erro ao verificar status');
          return;
        }

        await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
      }
    };

    poll();
    return () => { stopped = true; };
  }, [jobId, onDone, onError]);

  const pct = status && status.total_steps > 0
    ? Math.round((status.progress / status.total_steps) * 100)
    : 0;

  const steps = [
    { key: 'queued', label: 'Na fila' },
    { key: 'processing', label: 'Processando' },
    { key: 'completed', label: 'Concluído' },
  ];

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
    }}>
      <div style={{
        width: '100%',
        maxWidth: 480,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 16,
        padding: '32px 28px',
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
        boxShadow: '0 16px 48px rgba(0,0,0,0.4)',
      }}>
        {/* Icon + title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: 'rgba(36,76,90,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            {status?.status === 'completed'
              ? <CheckCircle size={22} style={{ color: '#4ade80' }} />
              : status?.status === 'failed'
                ? <XCircle size={22} style={{ color: '#f87171' }} />
                : <Loader2 size={22} style={{ color: 'var(--accent)', animation: 'spin 1s linear infinite' }} />
            }
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 15 }}>
              {status?.status === 'completed' ? 'Relatório pronto!' :
               status?.status === 'failed' ? 'Falha no processamento' :
               'Gerando relatório...'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {reportName}
            </div>
          </div>
        </div>

        {/* Progress bar */}
        {status?.status !== 'failed' && (
          <div>
            <div style={{
              height: 6,
              background: 'rgba(255,255,255,0.08)',
              borderRadius: 99,
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%',
                width: `${status?.status === 'completed' ? 100 : pct}%`,
                background: 'linear-gradient(90deg, var(--primary), var(--accent))',
                borderRadius: 99,
                transition: 'width 400ms ease',
              }} />
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
              {status?.current_step ?? 'Iniciando...'}
            </div>
          </div>
        )}

        {/* Steps indicator */}
        <div style={{ display: 'flex', gap: 8 }}>
          {steps.map((step, i) => {
            const active = status?.status === step.key;
            const done = (
              (step.key === 'queued' && ['processing', 'completed'].includes(status?.status ?? '')) ||
              (step.key === 'processing' && status?.status === 'completed')
            );
            return (
              <div key={step.key} style={{ flex: 1, textAlign: 'center' }}>
                <div style={{
                  height: 3,
                  borderRadius: 99,
                  background: done || active
                    ? (done ? 'var(--accent)' : 'rgba(242,200,17,0.5)')
                    : 'rgba(255,255,255,0.08)',
                  marginBottom: 6,
                  transition: 'background 300ms',
                }} />
                <span style={{
                  fontSize: 10,
                  color: active ? 'var(--accent)' : done ? 'var(--text-muted)' : 'var(--text-dim)',
                }}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
