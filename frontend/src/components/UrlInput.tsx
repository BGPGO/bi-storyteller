import { useState } from 'react';
import { BarChart2, ArrowRight } from 'lucide-react';

interface Props {
  onOpen: (url: string) => void;
}

export default function UrlInput({ onOpen }: Props) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setError('Cole a URL do relatório Power BI');
      return;
    }
    try {
      new URL(trimmed);
    } catch {
      setError('URL inválida — verifique o link do BI');
      return;
    }
    setError('');
    onOpen(trimmed);
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      gap: '40px',
    }}>
      {/* Logo area */}
      <div style={{ textAlign: 'center' }}>
        <div style={{
          width: 72,
          height: 72,
          borderRadius: 18,
          background: 'rgba(36,76,90,0.5)',
          border: '1px solid rgba(36,120,155,0.4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
        }}>
          <BarChart2 size={32} style={{ color: 'var(--accent)' }} />
        </div>

        <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 8 }}>
          BI Storyteller
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
          Gere relatórios executivos com storytelling a partir do seu dashboard
        </p>
      </div>

      {/* Input card */}
      <form
        onSubmit={handleSubmit}
        style={{
          width: '100%',
          maxWidth: 560,
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 16,
          padding: '28px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          boxShadow: '0 16px 48px rgba(0,0,0,0.4)',
        }}
      >
        <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}>
          Link do relatório Power BI
        </label>

        <input
          type="text"
          value={url}
          onChange={e => { setUrl(e.target.value); setError(''); }}
          placeholder="https://app.powerbi.com/reportEmbed?reportId=..."
          autoFocus
          style={{
            width: '100%',
            padding: '12px 14px',
            borderRadius: 10,
            border: `1px solid ${error ? 'rgba(239,68,68,0.6)' : 'var(--border)'}`,
            background: 'rgba(0,0,0,0.25)',
            color: 'var(--text)',
            fontSize: 13,
            outline: 'none',
            transition: 'border-color 150ms',
          }}
          onFocus={e => { e.currentTarget.style.borderColor = 'rgba(80,160,195,0.6)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = error ? 'rgba(239,68,68,0.6)' : 'var(--border)'; }}
        />

        {error && (
          <span style={{ fontSize: 12, color: 'rgba(239,68,68,0.9)' }}>{error}</span>
        )}

        <button type="submit" className="btn btn-accent" style={{ alignSelf: 'flex-end' }}>
          Abrir BI
          <ArrowRight size={15} />
        </button>
      </form>

      {/* How it works */}
      <div style={{
        display: 'flex',
        gap: 24,
        maxWidth: 560,
        width: '100%',
      }}>
        {[
          { n: '1', label: 'Cole o link', desc: 'URL pública do seu Power BI' },
          { n: '2', label: 'Interaja', desc: 'Aplique filtros normalmente' },
          { n: '3', label: 'Exporte', desc: 'Relatório com IA gerado em segundos' },
        ].map(step => (
          <div key={step.n} style={{
            flex: 1,
            padding: '14px',
            background: 'rgba(36,76,90,0.2)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            textAlign: 'center',
          }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: 'var(--accent-dim)',
              border: '1px solid rgba(242,200,17,0.3)',
              color: 'var(--accent)',
              fontSize: 12,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 10px',
            }}>
              {step.n}
            </div>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>{step.label}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{step.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
