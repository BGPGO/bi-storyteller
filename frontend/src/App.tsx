import { useCallback, useState } from 'react';
import { Download, RotateCcw } from 'lucide-react';

import UrlInput from './components/UrlInput';
import BIViewer from './components/BIViewer';
import { captureCurrentTab } from './lib/capture';
import { exportPage } from './lib/api';

// ── App state machine ─────────────────────────────────────────────────────────

type AppState =
  | { view: 'input' }
  | { view: 'viewer'; url: string; reportName: string }
  | { view: 'analyzing' }
  | { view: 'done'; pdfBlob: Blob; reportName: string; url: string }
  | { view: 'error'; message: string; url: string; reportName: string };

function extractReportName(url: string): string {
  try {
    const u = new URL(url);
    const name = u.searchParams.get('reportName') ?? u.searchParams.get('name');
    if (name) return decodeURIComponent(name);
  } catch { /* ignore */ }
  return 'Relatório BI';
}

export default function App() {
  const [state, setState] = useState<AppState>({ view: 'input' });

  const handleOpen = (url: string) => {
    setState({ view: 'viewer', url, reportName: extractReportName(url) });
  };

  const handleExportPage = useCallback(async () => {
    const s = state as Extract<AppState, { view: 'viewer' }>;
    try {
      // Capture FIRST — BI must be visible when the browser share dialog appears
      const screenshot = await captureCurrentTab();
      setState({ view: 'analyzing' });
      const blob = await exportPage(screenshot, s.reportName);
      setState({ view: 'done', pdfBlob: blob, reportName: s.reportName, url: s.url });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Erro desconhecido';
      setState({ view: 'error', message: msg, url: s.url, reportName: s.reportName });
    }
  }, [state]);

  const triggerDownload = (blob: Blob, name: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  if (state.view === 'input') {
    return <UrlInput onOpen={handleOpen} />;
  }

  if (state.view === 'viewer') {
    return (
      <BIViewer
        url={state.url}
        reportName={state.reportName}
        onBack={() => setState({ view: 'input' })}
        onExportPage={handleExportPage}
      />
    );
  }

  if (state.view === 'analyzing') {
    return (
      <Overlay>
        <Spinner />
        <p style={{ fontWeight: 600, fontSize: 15 }}>Analisando com IA...</p>
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          Claude está gerando o storytelling executivo do dashboard
        </p>
      </Overlay>
    );
  }

  if (state.view === 'done') {
    return (
      <Overlay>
        <div style={{
          width: 64, height: 64, borderRadius: 16,
          background: 'rgba(74,222,128,0.15)',
          border: '1px solid rgba(74,222,128,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Download size={28} style={{ color: '#4ade80' }} />
        </div>
        <p style={{ fontWeight: 600, fontSize: 16 }}>Relatório gerado!</p>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center' }}>
          O PDF foi baixado automaticamente.
        </p>
        <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
          <button className="btn" onClick={() => triggerDownload(state.pdfBlob, state.reportName)}>
            <Download size={14} />
            Baixar novamente
          </button>
          <button
            className="btn btn-ghost"
            onClick={() => setState({ view: 'viewer', url: state.url, reportName: state.reportName })}
          >
            <RotateCcw size={14} />
            Voltar ao BI
          </button>
          <button className="btn btn-ghost" onClick={() => setState({ view: 'input' })}>
            Novo relatório
          </button>
        </div>
      </Overlay>
    );
  }

  if (state.view === 'error') {
    return (
      <Overlay>
        <div style={{
          width: 64, height: 64, borderRadius: 16,
          background: 'rgba(239,68,68,0.12)',
          border: '1px solid rgba(239,68,68,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 28,
        }}>
          ⚠️
        </div>
        <p style={{ fontWeight: 600, fontSize: 16 }}>Algo deu errado</p>
        <p style={{
          color: 'var(--text-muted)', fontSize: 12, textAlign: 'center',
          maxWidth: 360, lineHeight: 1.6,
          background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
          padding: '10px 14px', borderRadius: 8,
        }}>
          {state.message}
        </p>
        <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
          <button
            className="btn"
            onClick={() => setState({ view: 'viewer', url: state.url, reportName: state.reportName })}
          >
            <RotateCcw size={14} />
            Tentar novamente
          </button>
          <button className="btn btn-ghost" onClick={() => setState({ view: 'input' })}>
            Novo relatório
          </button>
        </div>
      </Overlay>
    );
  }

  return null;
}

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 16, padding: 24,
    }}>
      {children}
    </div>
  );
}

function Spinner() {
  return (
    <>
      <div style={{
        width: 52, height: 52, borderRadius: '50%',
        border: '3px solid rgba(171,199,201,0.2)',
        borderTopColor: '#ABC7C9',
        animation: 'spin 0.9s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}
