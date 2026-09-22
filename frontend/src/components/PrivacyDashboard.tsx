import React, { useEffect, useState } from 'react';
import { Shield, ShieldAlert, ShieldCheck } from 'lucide-react';
import { api, PrivacyStats, POLLING_INTERVALS } from '../api';

export function PrivacyDashboard() {
  const [stats, setStats] = useState<PrivacyStats | null>(null);

  useEffect(() => {
    // Poll stats every 2 seconds
    const interval = setInterval(async () => {
      try {
        const res = await api.getPrivacyStats();
        setStats(res);
      } catch (err) {
        console.error("Failed to fetch stats", err);
      }
    }, POLLING_INTERVALS.PRIVACY_STATS);
    return () => clearInterval(interval);
  }, []);

  if (!stats) return null;

  return (
    <div className="card">
      <h2 className="card-title">
        <Shield color="var(--primary-color)" />
        Privacy Gateway
      </h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
        <div className="stat-box">
          <div className="stat-value">{stats.pii_detected_locally}</div>
          <div className="stat-label">Sensitive Elements</div>
        </div>
        
        <div className="stat-box">
          <div className="stat-value">{stats.pii_tokenized}</div>
          <div className="stat-label">Values Tokenized</div>
        </div>

        <div className="stat-box" style={{ gridColumn: 'span 2', backgroundColor: stats.raw_pii_sent_to_ai > 0 ? 'var(--danger-color)' : 'rgba(16, 185, 129, 0.1)', borderColor: stats.raw_pii_sent_to_ai > 0 ? 'var(--danger-color)' : 'var(--success-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
            {stats.raw_pii_sent_to_ai > 0 ? <ShieldAlert color={stats.raw_pii_sent_to_ai > 0 ? 'white' : 'var(--danger-color)'} /> : <ShieldCheck color="var(--success-color)" />}
            <div className="stat-value" style={{ color: stats.raw_pii_sent_to_ai > 0 ? 'white' : 'var(--success-color)' }}>
              {stats.raw_pii_sent_to_ai}
            </div>
          </div>
          <div className="stat-label" style={{ color: stats.raw_pii_sent_to_ai > 0 ? 'rgba(255,255,255,0.8)' : 'var(--success-color)' }}>
            Raw Secrets Leaked to Cloud
          </div>
        </div>

        <div className="stat-box" style={{ gridColumn: 'span 2' }}>
          <div className="stat-value">{stats.blocked_actions}</div>
          <div className="stat-label">Dangerous Actions Blocked</div>
        </div>
      </div>
    </div>
  );
}
