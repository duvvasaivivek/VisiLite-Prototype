import React from 'react';
import { ShieldAlert, CheckCircle, XCircle } from 'lucide-react';
import { api, TaskStatus } from '../api';

interface ActionGuardModalProps {
  task: TaskStatus | null;
  onResolved: () => void;
}

export function ActionGuardModal({ task, onResolved }: ActionGuardModalProps) {
  if (!task || task.status !== 'awaiting_confirmation') return null;

  const handleApprove = async () => {
    try {
      await api.approveAction(task.id, true);
      onResolved();
    } catch (e) {
      console.error(e);
    }
  };

  const handleBlock = async () => {
    try {
      await api.approveAction(task.id, false);
      onResolved();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2 className="card-title" style={{ color: 'var(--warning-color)' }}>
          <ShieldAlert />
          Action Confirmation Required
        </h2>
        
        <p style={{ margin: '1rem 0', color: 'var(--text-secondary)' }}>
          The agent is attempting to perform a potentially dangerous action. Please review and approve.
        </p>
        
        <div style={{ backgroundColor: 'var(--bg-color)', padding: '1rem', borderRadius: 'var(--radius-md)', fontFamily: 'monospace', fontSize: '0.875rem' }}>
          <strong>Action:</strong> {task.pending_confirmation?.action?.action}<br />
          <strong>Element ID:</strong> {task.pending_confirmation?.action?.element_id || 'N/A'}<br />
          <strong>Reason:</strong> {task.pending_confirmation?.reason}
        </div>

        <div className="modal-actions">
          <button className="btn btn-outline" onClick={handleBlock} style={{ borderColor: 'var(--danger-color)', color: 'var(--danger-color)' }}>
            <XCircle size={18} />
            Block
          </button>
          <button className="btn btn-success" onClick={handleApprove}>
            <CheckCircle size={18} />
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
