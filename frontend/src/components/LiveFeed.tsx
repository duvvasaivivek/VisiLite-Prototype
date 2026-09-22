import React, { useEffect, useRef } from 'react';
import { Activity, Code, MousePointer2, CheckCircle2, AlertCircle } from 'lucide-react';
import { TaskStatus } from '../api';

interface LiveFeedProps {
  task: TaskStatus | null;
}

export function LiveFeed({ task }: LiveFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [task?.message, task?.current_action]);

  if (!task) {
    return (
      <div className="feed-container" style={{ justifyContent: 'center', alignItems: 'center', color: 'var(--text-secondary)' }}>
        <Activity size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
        <p>Awaiting Instructions...</p>
      </div>
    );
  }

  const getIcon = () => {
    if (task.status === 'failed') return <AlertCircle className="feed-icon" color="var(--danger-color)" />;
    if (task.status === 'completed') return <CheckCircle2 className="feed-icon" color="var(--success-color)" />;
    if (task.current_action?.includes('click') || task.current_action?.includes('navigate')) return <MousePointer2 className="feed-icon" />;
    return <Code className="feed-icon" />;
  };

  return (
    <div className="feed-container">
      <div className="feed-item" style={{ borderLeft: '4px solid var(--primary-color)' }}>
        <Activity className="feed-icon" />
        <div className="feed-content">
          <div className="feed-title">Task Started</div>
          <div className="feed-desc">Instruction: {task.instruction}</div>
        </div>
      </div>

      {task.current_url && (
        <div className="feed-item">
          <MousePointer2 className="feed-icon" />
          <div className="feed-content">
            <div className="feed-title">Navigated to Page</div>
            <div className="feed-desc">{task.current_url}</div>
          </div>
        </div>
      )}

      {task.message && task.message !== 'TASK_STARTED' && (
        <div className="feed-item">
          {getIcon()}
          <div className="feed-content">
            <div className="feed-title">Action</div>
            <div className="feed-desc">{task.message}</div>
            
            {task.last_action?.reason && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                Reason: {task.last_action.reason}
              </div>
            )}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
