import { Button } from "./ui/button";
import addIcon from "../assets/icons/chat-add.svg";
import deleteIcon from "../assets/icons/delete.svg";
import { useChatsQuery, useDeleteChatMutation } from "../api/chat";
import "./ChatSidebar.css";

export default function ChatSidebar(parameters: {
  sessionIdentifier: string;
  currentChatId: number | null;
  onSelectChat: (chatId: number | null) => void;
}) {
  const { sessionIdentifier, currentChatId, onSelectChat } = parameters;
  const { data: chats = [], isLoading } = useChatsQuery(sessionIdentifier);
  const deleteChatMutation = useDeleteChatMutation(sessionIdentifier);

  return (
    <aside className="chatSidebarContainer w-64 shrink-0 border rounded-md bg-card p-3 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="font-semibold">Conversations</div>
        <Button variant="outline" onClick={() => {
          onSelectChat(null);
        }} aria-label="New chat" title="New chat" className="p-2 h-8 w-8">
          <img src={addIcon} alt="New" className="w-4 h-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-auto">
        {isLoading && <div className="text-sm opacity-70 p-2">Loading...</div>}
        {!isLoading && chats.length === 0 && (
          <div className="text-sm opacity-70 p-2">No conversations yet.</div>
        )}
        <ul className="space-y-1">
          {chats.map((c) => (
            <li key={c.id} className={`group flex items-center justify-between rounded px-2 py-1 cursor-pointer ${currentChatId === c.id ? "bg-accent" : "hover:bg-muted"}`}>
              <button className="text-left flex-1 truncate" onClick={() => onSelectChat(c.id)} title={c.title}>
                {c.title}
              </button>
              <Button variant="outline" onClick={(e) => {
                e.stopPropagation();
                deleteChatMutation.mutate(c.id);
              }} aria-label="Delete chat" title="Delete chat" className="p-2 h-8 w-8">
                <img src={deleteIcon} alt="Delete" className="w-4 h-4" />
              </Button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
