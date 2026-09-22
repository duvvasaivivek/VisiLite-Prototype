import React, { useState, useEffect } from 'react';
import { CommandBar } from './components/CommandBar';
import { LiveFeed } from './components/LiveFeed';
import { PrivacyDashboard } from './components/PrivacyDashboard';
import { ActionGuardModal } from './components/ActionGuardModal';
import { api, TaskStatus, HealthResponse, POLLING_INTERVALS } from './api';

function App() {
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  // Poll system health
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await api.getHealth();
        setHealth(res);
      } catch (err) {
        setHealth(null);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, POLLING_INTERVALS.HEALTH);
    return () => clearInterval(interval);
  }, []);

  // Poll task status
  useEffect(() => {
    if (!task || task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const res = await api.getTask(task.id);
        setTask(res);
      } catch (err) {
        console.error("Failed to poll task", err);
      }
    }, POLLING_INTERVALS.TASK);

    return () => clearInterval(interval);
  }, [task?.id, task?.status]);

  const handleTaskStarted = (newTask: TaskStatus) => {
    setTask(newTask);
  };

  const handleActionResolved = async () => {
    if (task) {
      const res = await api.getTask(task.id);
      setTask(res);
    }
  };

  const isTaskActive = task?.status === 'running' || task?.status === 'awaiting_confirmation';

  return (
    <div className="app-container">
      <ActionGuardModal task={task} onResolved={handleActionResolved} />
      
      <main className="main-content">
        <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '2rem' }}>
          VisiLite <span style={{ color: 'var(--text-secondary)', fontWeight: 'normal', fontSize: '1rem' }}>Web Client</span>
        </h1>
        
        <CommandBar onTaskStarted={handleTaskStarted} disabled={isTaskActive} />
        
        <LiveFeed task={task} />
      </main>

      <aside className="sidebar">
        <PrivacyDashboard />
        
        <div className="card">
          <h3 className="card-title" style={{ fontSize: '1rem' }}>System Status</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.875rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Backend</span>
              <span style={{ color: health?.status === 'ok' ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: 500 }}>
                {health ? 'Online' : 'Offline'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>LLM Planner</span>
              <span style={{ color: health?.llm_available ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: 500 }}>
                {health ? (health.llm_available ? `Connected (${health.llm_provider})` : 'Unavailable') : 'Unknown'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Current Task</span>
              <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>
                {task ? task.status.replace('_', ' ') : 'Idle'}
              </span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}

export default App;
