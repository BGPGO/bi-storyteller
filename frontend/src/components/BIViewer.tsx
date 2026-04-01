import { useState } from 'react';
import { ArrowLeft, Download, Monitor } from 'lucide-react';

interface Props {
  url: string;
  reportName: string;
  onBack: () => void;
  onExportPage: () => void;
}

export default function BIViewer({ url, reportName, onBack, onExportPage }: Props) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Top bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 16px',
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
        gap: 12,
        minHeight: 52,
      }}>
        <button className="btn btn-ghost" onClick={onBack} style={{ padding: '6px 12px', fontSize: 12 }}>
          <ArrowLeft size={14} />
          Voltar
        </button>

        <span style={{
          fontSize: 13,
          fontWeight: 500,
          color: 'var(--text-muted)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          flex: 1,
          textAlign: 'center',
        }}>
          {reportName}
        </span>

        {/* Export dropdown */}
        <div style={{ position: 'relative' }}>
          <button
            className="btn"
            onClick={() => setMenuOpen(v => !v)}
            style={{ padding: '7px 16px', fontSize: 12 }}
          >
            <Download size={13} />
            Exportar
          </button>

          {menuOpen && (
            <>
              {/* Click-outside overlay */}
              <div
                style={{ position: 'fixed', inset: 0, zIndex: 9 }}
                onClick={() => setMenuOpen(false)}
              />
              <div style={{
                position: 'absolute',
                top: 'calc(100% + 8px)',
                right: 0,
                width: 260,
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                borderRadius: 12,
                boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
                overflow: 'hidden',
                zIndex: 10,
              }}>
                <ExportOption
                  icon={<Monitor size={16} style={{ color: 'var(--accent)', flexShrink: 0 }} />}
                  label="Gerar Relatório com Storytelling"
                  desc="Captura a tela atual com seus filtros e gera análise executiva por IA"
                  onClick={() => { setMenuOpen(false); onExportPage(); }}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* BI iframe */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        <iframe
          src={url}
          style={{ width: '100%', height: '100%', border: 'none', display: 'block' }}
          allowFullScreen
          title={reportName}
        />
      </div>
    </div>
  );
}

function ExportOption({
  icon,
  label,
  desc,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  desc: string;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        padding: '14px 16px',
        border: 'none',
        background: hovered ? 'rgba(36,76,90,0.4)' : 'transparent',
        color: 'var(--text)',
        textAlign: 'left',
        cursor: 'pointer',
        transition: 'background 150ms',
      }}
    >
      <div style={{ marginTop: 2 }}>{icon}</div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 3 }}>{label}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>{desc}</div>
      </div>
    </button>
  );
}
