import { useEffect, useState } from "react";

import { runSocketUrl } from "../lib/api";
import type { AgentRun, RunEvent } from "../lib/runStore";

export function useMissionControlSocket(
  runId: string | null,
  onEvent: (event: RunEvent) => void,
  onSnapshot: (run: AgentRun) => void,
) {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!runId) return;
    let retry: number | undefined;
    let closed = false;
    let socket: WebSocket | undefined;

    const connect = () => {
      socket = new WebSocket(runSocketUrl(runId));
      socket.onopen = () => setConnected(true);
      socket.onmessage = (message) => {
        const data = JSON.parse(message.data) as RunEvent | { type: "run.snapshot"; payload: AgentRun };
        if (data.type === "run.snapshot" && !("run_id" in data)) {
          onSnapshot(data.payload as AgentRun);
        } else {
          onEvent(data as RunEvent);
        }
      };
      socket.onclose = (event) => {
        setConnected(false);
        if (!closed && event.code !== 1000) retry = window.setTimeout(connect, 1500);
      };
    };

    connect();
    return () => {
      closed = true;
      if (retry) window.clearTimeout(retry);
      socket?.close();
    };
  }, [runId, onEvent, onSnapshot]);

  return connected;
}
