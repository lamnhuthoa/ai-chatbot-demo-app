import { useEffect, useRef, useState } from "react";
import "./MessageList.css";
import type { ChatMessage } from "../types/chatTypes";
import { renderMarkdownToReact } from "../lib/markdownRenderer";
import { Button } from "./ui/button";

export default function MessageList(parameters: { messages: ChatMessage[]; isBusy: boolean; lastStreamingToken?: string; showThinking?: boolean }) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [isOverflowing, setIsOverflowing] = useState(false);

  // Auto-scroll only when the user adds a new message.
  // Do NOT auto-scroll when assistant message/stream updates occur.
  const prevLenRef = useRef(0);
  useEffect(() => {
    // If messages were cleared (e.g., starting a new chat), reset the tracker
    if (parameters.messages.length === 0) {
      prevLenRef.current = 0;
    }
    const len = parameters.messages.length;
    const prevLen = prevLenRef.current;
    if (len > prevLen) {
      const newlyAdded = parameters.messages.slice(prevLen);
      const hasNewUserMessage = newlyAdded.some((m) => m.role === "user");
      if (hasNewUserMessage) {
        endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      }
      prevLenRef.current = len;
    }
  }, [parameters.messages]);

  // Track scroll position & overflow
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const threshold = 2;
    const check = () => {
      setIsOverflowing(el.scrollHeight - el.clientHeight > threshold);
      setIsAtBottom(el.scrollTop + el.clientHeight >= el.scrollHeight - threshold);
    };
    check();
    const onScroll = () => check();
    el.addEventListener("scroll", onScroll, { passive: true });
    const id = window.setTimeout(check, 0);
    return () => {
      el.removeEventListener("scroll", onScroll);
      window.clearTimeout(id);
    };
  }, [parameters.messages, parameters.isBusy]);
  return (
    <div ref={listRef} className="messageListRoot border rounded-md bg-card">
      {parameters.messages.length === 0 && (
        <div className="messageListEmptyState">Ask something... or upload a file and ask about it.</div>
      )}

      {parameters.messages.map((message, index, arr) => {
        const isAssistant = message.role === "assistant";
        const isLast = index === arr.length - 1;
        const bubbleClassName = isAssistant ? "messageBubbleAssistant" : "messageBubbleUser";
        const streamingClass = isAssistant && isLast && parameters.isBusy ? " streaming" : "";

        return (
          <div key={message.messageIdentifier} className={`messageBubble ${bubbleClassName}${streamingClass}`}>
            {!isAssistant && message.attachmentFileNames && message.attachmentFileNames.length > 0 && (
              <div className="text-xs mb-1 opacity-70">
                Attachments: {message.attachmentFileNames.join(", ")}
              </div>
            )}
            {isAssistant ? (
              <div>{renderMarkdownToReact(message.content)}</div>
            ) : (
              <div>{message.content}</div>
            )}
          </div>
        );
      })}

      <div ref={endRef} />

      {isOverflowing && !isAtBottom && (
        <div className="scrollToBottomBar">
          <div className="scrollToBottomInner">
            <div className="scrollFade" />
            <Button
              className="scrollToButton"
              onClick={() => {
                if (listRef.current) {
                  listRef.current.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
                } else {
                  endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
                }
                setIsAtBottom(true);
              }}
            >
              Jump to latest
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
