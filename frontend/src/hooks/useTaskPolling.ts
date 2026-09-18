import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { PerfStats, PrivacyStats, TaskStatus } from "../types";

export function useTaskPolling(taskId: string | null) {
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [privacy, setPrivacy] = useState<PrivacyStats | null>(null);
  const [perf, setPerf] = useState<PerfStats | null>(null);
  const [audit, setAudit] = useState<Array<Record<string, unknown>>>([]);
  const [browser, setBrowser] = useState<{ url: string; title: string; screenshot: string } | null>(null);

  useEffect(() => {
    let timer: number;
    const tick = async () => {
      try {
        const [p, f, a, b] = await Promise.all([
          api.privacy(),
          api.performance(),
          api.audit(),
          api.browserState(),
        ]);
        setPrivacy(p);
        setPerf(f);
        setAudit(a);
        setBrowser(b);
        if (taskId) {
          setTask(await api.getTask(taskId));
        }
      } catch {
        /* dashboard keeps last good snapshot */
      }
      timer = window.setTimeout(tick, 900);
    };
    tick();
    return () => window.clearTimeout(timer);
  }, [taskId]);

  return { task, privacy, perf, audit, browser, setTask };
}
