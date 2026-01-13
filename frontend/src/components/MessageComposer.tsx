import { Button } from "./ui/button";
import sendIcon from "../assets/icons/send_white.svg";
import uploadIcon from "../assets/icons/upload.svg";
import { Select } from "./ui/select";
import { Textarea } from "./ui/textarea";
import "./MessageComposer.css";

export default function MessageComposer(parameters: {
  messageValue: string;
  onMessageValueChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
  model: string;
  onModelChange: (value: string) => void;
  attachments?: File[];
  onAttachmentsSelected?: (files: File[]) => void;
  onAttachmentRemoved?: (index: number) => void;
}) {
  const hasSendableMessage = parameters.messageValue.trim().length > 0;
  const characterCount = parameters.messageValue.length;
  const rows = characterCount > 50 ? 5 : 1;

  return (
    <div className="messageComposerRoot border rounded-md p-3 bg-card">
      <div className="messageComposerRow flex gap-2 items-start">
        <div className="messageComposerArea">
          {parameters.attachments && parameters.attachments.length > 0 && (
            <div className="mb-2 flex items-center gap-2 flex-wrap">
              {parameters.attachments.map((file, idx) => (
                <span
                  key={idx}
                  className="text-xs px-2 py-1 rounded-full bg-muted border inline-flex items-center gap-1"
                >
                  {file.name}
                  <button
                    type="button"
                    aria-label="Remove attachment"
                    title="Remove attachment"
                    className="ml-1 w-4 h-4 flex items-center justify-center rounded hover:bg-gray-200"
                    disabled={parameters.disabled}
                    onClick={() =>
                      parameters.onAttachmentRemoved &&
                      parameters.onAttachmentRemoved(idx)
                    }
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="messageComposerInput">
            <Textarea
              value={parameters.messageValue}
              onChange={(event) =>
                parameters.onMessageValueChange(event.target.value)
              }
              disabled={parameters.disabled}
              rows={rows}
              className="flex-1"
              draggable={false}
              placeholder="Type your message here..."
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  parameters.onSend();
                }
              }}
            />
            <div className="messageComposerButtons">
              <input
                type="file"
                hidden
                id="composer-file-input"
                accept=".pdf,.txt,.csv"
                multiple
                onChange={(e) => {
                  const files = e.currentTarget.files
                    ? Array.from(e.currentTarget.files)
                    : [];
                  if (files.length && parameters.onAttachmentsSelected)
                    parameters.onAttachmentsSelected(files);
                  e.currentTarget.value = "";
                }}
              />
              <Button
                disabled={!hasSendableMessage || parameters.disabled}
                onClick={parameters.onSend}
                aria-label="Send"
                title="Send"
                className="p-2 h-9 w-9 flex items-center justify-center bg-black"
              >
                <img src={sendIcon} alt="Send" className="w-5 h-5" />
              </Button>
            </div>
          </div>
          <div className="messageComposerFeatures mt-2 flex items-center gap-2">
            <Select
              value={parameters.model}
              onChange={(event) => parameters.onModelChange(event.target.value)}
              disabled={parameters.disabled}
              className="messageComposerModelSelect w-48"
            >
              <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              <option value="llama3.2">llama3.2</option>
            </Select>

            <Button
              variant="secondary"
              disabled={parameters.disabled}
              onClick={() =>
                document.getElementById("composer-file-input")?.click()
              }
              className="p-2 h-9 w-9 mr-1 bg-black"
              aria-label="Attach file"
              title="Attach file"
            >
              <img src={uploadIcon} alt="Upload" className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
