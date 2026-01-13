export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  messageIdentifier: string;
  role: ChatRole;
  content: string;
  createdAtEpochMilliseconds: number;
  attachmentFileNames?: string[];
};

export type ChatResponse = {
  text: string;
};

export type FileUploadResponse = {
  filename: string;
  tokens?: number;
  pages?: number;
  columns?: string[];
  rag_indexed?: boolean;
};
