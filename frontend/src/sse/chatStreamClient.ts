import { SSE } from "sse.js";
import { BASE_API_URL } from "../api/client.ts";

// Ensure we always use an absolute http(s) URL to avoid CORS/network failures
export const API_BASE: string = BASE_API_URL || "http://localhost:8000";
const STREAM_URL = `${API_BASE}/api/agents/stream`;
export type ChatStreamCallbacks = {
  onToken: (token: string) => void;
  onCompleted: () => void;
  onError: (error: Error) => void;
  onThinking?: () => void;
  onStart?: (meta: { chatId?: number }) => void;
};

export function startChatStream(parameters: {
  sessionIdentifier: string;
  message: string;
  chatId?: number;
  callbacks: ChatStreamCallbacks;
}): () => void {
  const urlWithSession = `${STREAM_URL}?session_id=${encodeURIComponent(parameters.sessionIdentifier)}`;
  const eventSource = new SSE(urlWithSession, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // Backend expects: { prompt, temperature }
    payload: JSON.stringify({
      prompt: parameters.message,
      temperature: 0.3,
  chat_id: parameters.chatId ?? undefined,
    }),
  });

  // Throttle UI updates to make the typing feel more natural
  const PACE_MS = 15; // emit one token every ~15ms
  const queue: string[] = [];
  let drainTimer: number | null = null;
  let doneReceived = false;

  const ensureDrain = () => {
    if (drainTimer !== null) return;
    drainTimer = window.setInterval(() => {
      if (queue.length > 0) {
        const token = queue.shift() as string;
        parameters.callbacks.onToken(token);
        return;
      }
      if (doneReceived) {
        if (drainTimer !== null) {
          window.clearInterval(drainTimer);
          drainTimer = null;
        }
        parameters.callbacks.onCompleted();
      }
    }, PACE_MS);
  };

  eventSource.addEventListener("start", (event: MessageEvent) => {
    try {
      const payload = JSON.parse(event.data ?? "{}");
      const chatId = payload?.chatId as number | undefined;
      if (parameters.callbacks.onStart) parameters.callbacks.onStart({ chatId });
    } catch {
      if (parameters.callbacks.onStart) parameters.callbacks.onStart({});
    }
  });

  // Optional: react to server-provided thinking state
  eventSource.addEventListener("BOT_THINKING", () => {
    if (parameters.callbacks.onThinking) parameters.callbacks.onThinking();
  });

  // Receive incremental content chunks
  eventSource.addEventListener("BOT_Response", (event: MessageEvent) => {
    try {
      const payload = JSON.parse(event.data ?? "{}");
      const token = String(payload.content ?? "");
      if (token) {
        queue.push(token);
        ensureDrain();
      }
    } catch {
      const token = String(event.data || "").replace(/\\n/g, "\n");
      if (token) {
        queue.push(token);
        ensureDrain();
      }
    }
  });

  eventSource.addEventListener("done", () => {
    eventSource.close();
    doneReceived = true;
    ensureDrain();
  });

  // Backend "error" event payload
  eventSource.addEventListener("error", (event: MessageEvent) => {
    eventSource.close();
    if (drainTimer !== null) {
      window.clearInterval(drainTimer);
      drainTimer = null;
    }
    try {
      const payload = JSON.parse(event.data ?? "{}");
      const message = payload?.message || "Streaming connection failed";
      parameters.callbacks.onError(new Error(message));
    } catch {
  const raw = event?.data ?? "";
  const message = typeof raw === "string" && raw.length > 0 ? raw : "Streaming connection failed";
  parameters.callbacks.onError(new Error(message));
    }
  });

  eventSource.stream();

  return () => {
    eventSource.close();
    if (drainTimer !== null) {
      window.clearInterval(drainTimer);
    }
  };
}
