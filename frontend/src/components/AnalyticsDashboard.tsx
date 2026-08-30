import React from 'react';

interface AnalyticsDashboardProps {
  analytics: {
    total_queries: number;
    answered_queries: number;
    unanswered_queries_count: number;
    unanswered_list: string[];
    heatmap: Record<string, number>;
  };
  capsuleSlug: string;
  authToken: string;
  setView: (view: 'upload' | 'processing' | 'ready' | 'chat' | 'password_gate' | 'expired' | 'dashboard' | 'global_dashboard') => void;
  APP_URL: string;
  showToast: (msg: string) => void;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  analytics,
  capsuleSlug,
  authToken,
  setView,
  APP_URL,
  showToast
}) => {
  return (
    <div className="dropzone-container" style={{ maxWidth: '800px', gap: '2.5rem' }}>
      <button className="back-nav" onClick={() => setView(authToken ? 'global_dashboard' : 'ready')}>
        ← Back
      </button>
      
      <div style={{ textAlign: 'left' }}>
        <h1 className="hero-title" style={{ fontSize: '2.5rem' }}>Capsule Dashboard</h1>
        <p className="hero-subtitle" style={{ margin: 0 }}>Metrics and engagement report for capsule: <strong>{capsuleSlug}</strong></p>
      </div>

      {/* Metrics cards */}
      <div className="dashboard-grid">
        <div className="metric-card">
          <div className="metric-num">{analytics.total_queries}</div>
          <div className="metric-title">Total Questions</div>
        </div>
        <div className="metric-card">
          <div className="metric-num" style={{ color: 'var(--accent-color)' }}>{analytics.answered_queries}</div>
          <div className="metric-title">Answered Queries</div>
        </div>
        <div className="metric-card">
          <div className="metric-num" style={{ color: '#FCA5A5' }}>{analytics.unanswered_queries_count}</div>
          <div className="metric-title">Unanswered (Gaps)</div>
        </div>
      </div>

      {/* Heatmap Section */}
      <div className="heatmap-card" style={{ textAlign: 'left' }}>
        <h3 className="suggested-title">Query Heatmap (Page Query Hotspots)</h3>
        <p style={{ color: 'var(--text-muted-light)', fontSize: '0.85rem' }}>Visualizing which document pages are query targets.</p>
        
        <div className="heatmap-container">
          {Object.keys(analytics.heatmap).length === 0 ? (
            <p style={{ color: 'var(--text-muted-light)', fontStyle: 'italic', margin: 'auto' }}>No page analytics logged yet.</p>
          ) : (
            Object.entries(analytics.heatmap).map(([page, count]) => {
              const maxCount = Math.max(...Object.values(analytics.heatmap), 1);
              const percentage = (count / maxCount) * 100;
              return (
                <div key={page} className="heatmap-column">
                  <div 
                    className="heatmap-bar" 
                    style={{ height: `${percentage}%` }}
                    title={`Page ${page}: ${count} queries`}
                  />
                  <span className="heatmap-label">Pg {page}</span>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Unanswered Gaps Section */}
      <div className="unanswered-card" style={{ textAlign: 'left' }}>
        <h3 className="suggested-title" style={{ color: '#EF4444' }}>Reader Gaps Log (Unanswered Questions)</h3>
        <p style={{ color: 'var(--text-muted-light)', fontSize: '0.85rem' }}>These questions returned "This document doesn't cover that." indicating content gaps.</p>
        
        <div className="unanswered-list">
          {analytics.unanswered_list.length === 0 ? (
            <p style={{ color: 'var(--text-muted-light)', fontStyle: 'italic' }}>No unanswered questions logged. Excellent document coverage!</p>
          ) : (
            analytics.unanswered_list.map((q, idx) => (
              <div key={idx} className="unanswered-item">
                "{q}"
              </div>
            ))
          )}
        </div>
      </div>

      {/* QR Code and Embed Code snippets grid */}
      <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
        <div className="embed-card" style={{ textAlign: 'left', margin: 0 }}>
          <h3 className="suggested-title">QR Code</h3>
          <p style={{ color: 'var(--text-muted-light)', fontSize: '0.85rem' }}>Scan this code to instantly access the reader interface on a mobile device.</p>
          <div className="qr-container" style={{ margin: '1.5rem auto 0', border: '1px solid var(--border-dark)', backgroundColor: 'var(--primary-bg-alt)' }}>
            <img 
              src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(`${APP_URL}/d/${capsuleSlug}`)}`} 
              alt="QR Code" 
              className="qr-image" 
              style={{ filter: 'invert(1) hue-rotate(180deg)', backgroundColor: '#fff', padding: '8px', borderRadius: '8px' }} 
            />
            <span className="qr-text" style={{ color: 'var(--text-muted-light)' }}>Scan to open reader</span>
          </div>
        </div>

        <div className="embed-card" style={{ textAlign: 'left', margin: 0 }}>
          <h3 className="suggested-title">Embed Widget</h3>
          <p style={{ color: 'var(--text-muted-light)', fontSize: '0.85rem' }}>Paste this iframe code into your website or blog to embed a compact chat window.</p>
          <div className="embed-code-box">
            {`<iframe src="${APP_URL}/d/${capsuleSlug}?embed=true" width="100%" height="600" style="border:1px solid rgba(255,255,255,0.08); border-radius:12px; background:transparent;"></iframe>`}
          </div>
          <button 
            className="copy-btn" 
            onClick={() => {
              navigator.clipboard.writeText(`<iframe src="${APP_URL}/d/${capsuleSlug}?embed=true" width="100%" height="600" style="border:1px solid rgba(255,255,255,0.08); border-radius:12px; background:transparent;"></iframe>`)
                .then(() => showToast('Embed code copied!'))
                .catch(() => showToast('Failed to copy.'));
            }}
          >
            Copy Embed Code
          </button>
        </div>
      </div>
    </div>
  );
};
