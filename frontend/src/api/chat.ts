import { httpClient } from "./client";
import { useQuery, useMutation } from "@tanstack/react-query";
import type { QueryKey } from "@tanstack/react-query";
import type { FileUploadResponse } from "../types/chatTypes";
import { queryClient } from "@/utils/reactQueryUtil";

// Types used by hooks
export type AgentPreference = {
  session_id: string;
  provider: string;
  model: string;
};
export type HistoryTurn = {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
};
export type HistoryResponse = { session_id: string; items: HistoryTurn[] };
export type ChatListItem = { id: number; session_id: string; title: string };
export type ChatMessageItem = {
  id: number;
  chat_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

// React Query hooks and keys only
export const chatsQueryKey = (sessionIdentifier: string): QueryKey => [
  "chats",
  sessionIdentifier,
];
export const chatMessagesQueryKey = (chatId: number): QueryKey => [
  "chat-messages",
  chatId,
];
export const agentPreferencesQueryKey = (
  sessionIdentifier: string
): QueryKey => ["agent-preferences", sessionIdentifier];


// React Query hooks
export function useChatsQuery(sessionIdentifier: string) {
  return useQuery({
    queryKey: chatsQueryKey(sessionIdentifier),
    queryFn: async () => {
      const response = await httpClient.get<ChatListItem[]>("/api/chats/", {
        params: { session_id: sessionIdentifier },
      });
      return response.data;
    },
  });
}

export function useChatMessagesQuery(
  chatId: number,
  options?: { enabled?: boolean }
) {
  const enabled = options?.enabled ?? true;
  return useQuery({
    queryKey: chatMessagesQueryKey(chatId),
    queryFn: async () => {
      const response = await httpClient.get<ChatMessageItem[]>(
        `/api/chats/${chatId}/messages`
      );
      return response.data;
    },
    enabled,
    // Keep previously loaded messages while a refetch is in flight
    placeholderData: (prev) => prev,
    // So we don't refetch too eagerly while user is typing/streaming
    staleTime: 5000,
  });
}

export function useCreateChatMutation(sessionIdentifier: string) {
  return useMutation({
    mutationFn: async (title?: string) => {
      const response = await httpClient.post<ChatListItem>("/api/chats/", {
        session_id: sessionIdentifier,
        title: title || "New chat",
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: chatMessagesQueryKey(data.id)
      })
      queryClient.invalidateQueries({
        queryKey: chatsQueryKey(sessionIdentifier),
        refetchType: "active",
      });
    },
  });
}

export function useDeleteChatMutation(sessionIdentifier: string) {
  return useMutation({
    mutationFn: async (chatId: number) => {
      const response = await httpClient.delete<ChatListItem>(
        `/api/chats/${chatId}`
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: chatsQueryKey(sessionIdentifier),
        refetchType: "active",
      });
    },
  });
}

export function useAgentPreferencesQuery(sessionIdentifier: string) {
  return useQuery({
    queryKey: agentPreferencesQueryKey(sessionIdentifier),
    queryFn: async () => {
      const response = await httpClient.get<AgentPreference>(
        "/api/agents/preferences",
        {
          params: { session_id: sessionIdentifier },
        }
      );
      return response.data;
    },
  });
}

export function useSetAgentPreferencesMutation(sessionIdentifier: string) {
  return useMutation({
    mutationFn: async (payload: {
      provider: "gemini" | "ollama";
      model: string;
    }) => {
      const response = await httpClient.post<AgentPreference>(
        "/api/agents/preferences",
        { provider: payload.provider, model: payload.model },
        { params: { session_id: sessionIdentifier } }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: agentPreferencesQueryKey(sessionIdentifier),
        refetchType: "active",
      });
    },
  });
}

export function useConversationHistoryQuery(
  sessionIdentifier: string,
  limit?: number,
  options?: { enabled?: boolean }
) {
  const enabled = options?.enabled ?? true;
  return useQuery({
    queryKey: ["conversation-history", sessionIdentifier, limit ?? null],
    queryFn: async () => {
      const response = await httpClient.get<HistoryResponse>(
        "/api/agents/history",
        {
          params: { session_id: sessionIdentifier, limit },
        }
      );
      return response.data;
    },
    enabled,
  });
}

export function useUploadContextMutation(sessionIdentifier: string) {
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const response = await httpClient.post<FileUploadResponse>(
        "/api/files/upload",
        formData,
        { params: { session_id: sessionIdentifier } }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["uploaded-context", sessionIdentifier],
        refetchType: "active",
      });
    },
  });
}

export function useClearContextMutation(sessionIdentifier: string) {
  return useMutation({
    mutationFn: async () => {
      const response = await httpClient.delete<{
        status: string;
        session_id: string;
      }>("/api/files/clear", { params: { session_id: sessionIdentifier } });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["uploaded-context", sessionIdentifier],
        refetchType: "active",
      });
    },
  });
}
