export function getOrCreateSessionIdentifier(): string {
  const storageKey = "chat_session_identifier";
  const existingSessionIdentifier = localStorage.getItem(storageKey);

  if (existingSessionIdentifier) {
    return existingSessionIdentifier;
  }

  const newSessionIdentifier = crypto.randomUUID();
  localStorage.setItem(storageKey, newSessionIdentifier);
  return newSessionIdentifier;
}
