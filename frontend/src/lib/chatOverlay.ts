import type { ChatMessage } from "../types/chatTypes";

export function createChatMessage(params: { role: "user" | "assistant"; content: string }): ChatMessage {
  return {
    messageIdentifier: crypto.randomUUID(),
    role: params.role,
    content: params.content,
    createdAtEpochMilliseconds: Date.now(),
  };
}

export function appendAssistantToken(
  messages: ChatMessage[],
  assistantMessageIdentifier: string,
  token: string
): ChatMessage[] {
  return messages.map((m) => {
    if (m.messageIdentifier !== assistantMessageIdentifier) return m;
    if (m.content === "Thinking...") return { ...m, content: token };
    return { ...m, content: m.content + token };
  });
}

export function setAssistantContent(
  messages: ChatMessage[],
  assistantMessageIdentifier: string,
  content: string,
  onlyIfEmpty?: boolean
): ChatMessage[] {
  return messages.map((m) => {
    if (m.messageIdentifier !== assistantMessageIdentifier) return m;
    if (onlyIfEmpty && m.content) return m;
    return { ...m, content };
  });
}

export function mergeMessages(base: ChatMessage[], overlay: ChatMessage[]): ChatMessage[] {
  // Base is ground truth; never remove items once shown
  const result = [...base];

  // Dedupe overlay by ID for stability
  const ids = new Set<string>();
  const overlayDedup = overlay.filter((m) => (ids.has(m.messageIdentifier) ? false : (ids.add(m.messageIdentifier), true)));

  // Normalize content and prepare role-based sets for simple dedupe
  const norm = (s: string) => s.trim();
  const baseUser = new Set(base.filter((b) => b.role === "user").map((b) => norm(b.content)));
  const baseAssistant = new Set(base.filter((b) => b.role === "assistant").map((b) => norm(b.content)));

  // Include overlays only if their content for that role isn't already in base
  const userOverlay = overlayDedup.filter((m) => m.role === "user" && !baseUser.has(norm(m.content)));
  const assistantOverlay = overlayDedup.filter((m) => m.role === "assistant" && !baseAssistant.has(norm(m.content)));

  return [...result, ...userOverlay, ...assistantOverlay];
}
