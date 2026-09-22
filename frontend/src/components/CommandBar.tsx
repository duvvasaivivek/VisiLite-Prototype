import React, { useState } from 'react';
import { Send, Globe } from 'lucide-react';
import { api, TaskStatus } from '../api';

interface CommandBarProps {
  onTaskStarted: (task: TaskStatus) => void;
  disabled: boolean;
}

export function CommandBar({ onTaskStarted, disabled }: CommandBarProps) {
  const [instruction, setInstruction] = useState('');
  const [startUrl, setStartUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!instruction.trim()) return;

    setLoading(true);
    try {
      const task = await api.createTask({
        instruction,
        start_url: startUrl || undefined
      });
      setInstruction('');
      onTaskStarted(task);
    } catch (err) {
      console.error(err);
      alert("Failed to start task. Is backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ marginBottom: '2rem' }}>
      <h2 className="card-title">Command VisiLite</h2>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div className="input-group">
          <div style={{ position: 'relative', flex: 1 }}>
            <Globe className="feed-icon" size={18} style={{ position: 'absolute', left: '1rem', top: '0.85rem' }} />
            <input
              type="text"
              className="input"
              style={{ paddingLeft: '2.5rem' }}
              placeholder="Start URL (optional)"
              value={startUrl}
              onChange={(e) => setStartUrl(e.target.value)}
              disabled={disabled || loading}
            />
          </div>
        </div>
        <div className="input-group">
          <input
            type="text"
            className="input"
            placeholder="e.g. Log into my account and check my balance..."
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            disabled={disabled || loading}
          />
          <button type="submit" className="btn btn-primary" disabled={!instruction.trim() || disabled || loading}>
            <Send size={18} />
            {loading ? "Starting..." : "Run"}
          </button>
        </div>
      </form>
    </div>
  );
}
