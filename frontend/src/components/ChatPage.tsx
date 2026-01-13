import { useMemo, useRef, useState } from "react";
// MUI removed; using tailwind utility classes for layout and text
import { toast } from "react-toastify";

import type { ChatMessage, FileUploadResponse } from "../types/chatTypes";
import { getOrCreateSessionIdentifier } from "../utils/sessionUtil";
import {
  chatMessagesQueryKey,
  useAgentPreferencesQuery,
  useSetAgentPreferencesMutation,
  useChatMessagesQuery,
  useUploadContextMutation,
  useCreateChatMutation,
} from "../api/chat";
import { startChatStream } from "../sse/chatStreamClient";
import { generateTitleFromPrompt } from "../lib/chatTitle";
import { appendAssistantToken, createChatMessage, mergeMessages, setAssistantContent } from "../lib/chatOverlay";

import MessageList from "./MessageList";
import MessageComposer from "./MessageComposer";
import StatusBar from "./StatusBar";
import ChatSidebar from "./ChatSidebar";

import "./ChatPage.css";
import { queryClient } from "@/utils/reactQueryUtil";


export default function ChatPage() {
  const sessionIdentifier = useMemo(() => getOrCreateSessionIdentifier(), []);

  // Messages from server via React Query; overlay holds in-flight user/assistant placeholders
  const [draftMessage, setDraftMessage] = useState<string>("");
  const [selectedModel, setSelectedModel] = useState<string>("llama3.2");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [currentChatId, setCurrentChatId] = useState<number | null>(null);
  const [overlayMessages, setOverlayMessages] = useState<ChatMessage[]>([]);
  const [pendingAttachments, setPendingAttachments] = useState<File[]>([]);

  const cancelStreamingFunctionReference = useRef<null | (() => void)>(null);

  const fileUploadMutation = useUploadContextMutation(sessionIdentifier);
  const createChatMutation = useCreateChatMutation(sessionIdentifier);

  const isBusy = fileUploadMutation.isPending || isStreaming;

  const { data: agentPref } = useAgentPreferencesQuery(sessionIdentifier);
  const setPrefMutation = useSetAgentPreferencesMutation(sessionIdentifier);
  const displayModel = selectedModel || agentPref?.model || "llama3.2";

  function appendAssistantTokenToMessage(parameters: { assistantMessageIdentifier: string; token: string }) {
    setOverlayMessages((prev) => appendAssistantToken(prev, parameters.assistantMessageIdentifier, parameters.token));
  }
  function setAssistantMessageContent(parameters: { assistantMessageIdentifier: string; content: string; onlyIfEmpty?: boolean }) {
    setOverlayMessages((prev) => setAssistantContent(prev, parameters.assistantMessageIdentifier, parameters.content, parameters.onlyIfEmpty));
  }

  // Attachments are selected via the composer chip; uploads happen at send time

  async function handleSendMessage() {
    const trimmedMessage = draftMessage.trim();
    if (!trimmedMessage || isBusy) return;
    // Ensure a chat exists before streaming
    let chatIdForSend = currentChatId;
    if (chatIdForSend == null) {
      try {
        const optimisticTitle = generateTitleFromPrompt(trimmedMessage);
        const created = await createChatMutation.mutateAsync(optimisticTitle);
        chatIdForSend = created.id;
        setCurrentChatId(chatIdForSend);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to create chat";
        toast.error(message);
        return;
      }
    }

    setStatusMessage(null);
    setDraftMessage("");
    setIsStreaming(true);

    // If there's a pending attachment, upload it first (so RAG/context is ready)
  const attachmentNamesForThisMessage: string[] = [];
    if (pendingAttachments.length > 0) {
      for (const file of pendingAttachments) {
        try {
          const resp = await fileUploadMutation.mutateAsync(file);
          const name = (resp as FileUploadResponse).filename;
          attachmentNamesForThisMessage[attachmentNamesForThisMessage.length] = name;
        } catch (e) {
          const msg = e instanceof Error ? e.message : "File upload failed";
          toast.error(msg);
          return; // abort send if any upload failed
        }
      }
      setPendingAttachments([]);
    }

    // Add user message (overlay) with optional attachment name
    setOverlayMessages((previous) => [
      ...previous,
      { ...createChatMessage({ role: "user", content: trimmedMessage }), attachmentFileNames: attachmentNamesForThisMessage },
    ]);

    // Add one assistant placeholder message
    const assistantMessageIdentifier = crypto.randomUUID();
    setOverlayMessages((previous) => [
      ...previous,
      {
        messageIdentifier: assistantMessageIdentifier,
        role: "assistant",
        content: "",
        createdAtEpochMilliseconds: Date.now(),
      },
    ]);

    // Persist the latest preference just-in-time (non-blocking)
    const provider = displayModel.startsWith("gemini") ? "gemini" : "ollama";
    setPrefMutation.mutate({ provider, model: displayModel });

    // Start SSE stream
    const cancelStreamingFunction = startChatStream({
      sessionIdentifier,
      message: trimmedMessage,
      chatId: chatIdForSend ?? undefined,
      callbacks: {
        onStart: ({ chatId }) => {
          if (chatId && chatId !== currentChatId) {
            setCurrentChatId(chatId);
          }
        },
        onThinking: () => {
          // Show Thinking... in the assistant placeholder bubble if still empty
          setAssistantMessageContent({
            assistantMessageIdentifier,
            content: "Thinking...",
            onlyIfEmpty: true,
          });
        },
        onToken: (token) =>
          appendAssistantTokenToMessage({ assistantMessageIdentifier, token }),
        onCompleted: () => {
          setIsStreaming(false);
          cancelStreamingFunctionReference.current = null;
          // Refetch messages so persisted assistant reply is added; keep overlay in place
          if (currentChatId != null) {
            queryClient.invalidateQueries({
              queryKey: chatMessagesQueryKey(currentChatId),
            });
          }
        },
        onError: (error) => {
          setIsStreaming(false);
          cancelStreamingFunctionReference.current = null;
          setStatusMessage(error.message);
          toast.error(error.message);
        },
      },
    });

    cancelStreamingFunctionReference.current = cancelStreamingFunction;
  }

  const headerSubtitle = "Model: " + displayModel;

  const { data: chatItems } = useChatMessagesQuery(currentChatId ?? -1, {
    enabled: currentChatId != null,
  });
  const baseMessages: ChatMessage[] = useMemo(
    () =>
      (chatItems ?? []).map((m) => ({
        messageIdentifier: `${m.chat_id}:${m.id}`,
        role: m.role,
        content: m.content,
        createdAtEpochMilliseconds: Date.parse(m.created_at),
      })),
    [chatItems]
  );
  const mergedMessages: ChatMessage[] = useMemo(
    () => mergeMessages(baseMessages, overlayMessages),
    [baseMessages, overlayMessages]
  );
  // When no chat is selected (e.g., after clicking Add New), force an empty list
  // so we don't render placeholderData from the last chat.
  const shownMessages: ChatMessage[] = currentChatId == null ? [] : mergedMessages;

  return (
    <div className="chatPageRoot">
      <div className="w-full border-b bg-card">
        <div className="px-3 py-3 flex items-center justify-between w-full">
          <div className="text-lg font-semibold">
            Alfred - Personal Assistant
          </div>
          <div className="text-sm text-muted-foreground">{headerSubtitle}</div>
        </div>
      </div>
      <div className="chatPageWrapper">
        <ChatSidebar
          sessionIdentifier={sessionIdentifier}
          currentChatId={currentChatId}
          onSelectChat={(id) => {
            // If selecting a new blank conversation, clear current UI state
            if (id == null) {
              if (cancelStreamingFunctionReference.current) {
                cancelStreamingFunctionReference.current();
                cancelStreamingFunctionReference.current = null;
              }
              setIsStreaming(false);
              setStatusMessage(null);
              setOverlayMessages([]);
              setDraftMessage("");
            }
            // Switching to a different existing conversation: clear transient overlay state
            if (id != null && id !== currentChatId) {
              if (cancelStreamingFunctionReference.current) {
                cancelStreamingFunctionReference.current();
                cancelStreamingFunctionReference.current = null;
              }
              setIsStreaming(false);
              setStatusMessage(null);
              setOverlayMessages([]);
              setDraftMessage("");
            }
            setCurrentChatId(id);
          }}
        />
        <div className="max-w-5xl mx-auto px-4 py-4 chatPageContainer flex gap-4">
          <div className="flex-1 min-w-0 chatMain">
            {/* <div className="chatPageControls border rounded-md p-3 bg-card mb-4">
              <StatusBar sessionIdentifier={sessionIdentifier} statusMessage={statusMessage} />
            </div> */}

            <div className="messageListWrapper">
              <MessageList messages={shownMessages} isBusy={isBusy} />
            </div>

            <MessageComposer
              messageValue={draftMessage}
              onMessageValueChange={setDraftMessage}
              onSend={handleSendMessage}
              disabled={isBusy}
              model={displayModel}
              attachments={pendingAttachments}
              onAttachmentsSelected={(files) => setPendingAttachments((prev) => [...prev, ...files])}
              onAttachmentRemoved={(index) => setPendingAttachments((prev) => prev.filter((_, i) => i !== index))}
              onModelChange={(value) => {
                setSelectedModel(value);
                const provider = value.startsWith("gpt-")
                  ? "openai"
                  : value.startsWith("gemini")
                  ? "gemini"
                  : "ollama";
                // Persist immediately when model changes (non-blocking)
                setPrefMutation.mutate({ provider, model: value });
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
