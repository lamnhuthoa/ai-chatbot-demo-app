import { Button } from "./ui/button";
import uploadIcon from "../assets/icons/upload.svg";
import deleteIcon from "../assets/icons/delete.svg";
import { useRef } from "react";
import "./FileUploadControl.css";

export default function FileUploadControl(parameters: {
  disabled: boolean;
  onFileSelected: (file: File) => void;
  fileName?: string | null;
  onRemove?: () => void;
}) {
  const { disabled, onFileSelected, fileName, onRemove } = parameters;
  const canRemove = !!fileName && typeof onRemove === "function";

  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="fileUploadControlRoot">
      <div className="fileUploadControlActions">
        <input
          ref={inputRef}
          className="fileUploadControlInput"
          hidden
          type="file"
          accept=".pdf,.txt,.csv"
          onChange={(event) => {
            const selectedFile = event.target.files?.[0];
            if (selectedFile) {
              onFileSelected(selectedFile);
            }
            // reset input so selecting the same file again still triggers change
            event.currentTarget.value = "";
          }}
        />
        <Button
          type="button"
          variant="default"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
          aria-label="Upload file"
          title="Upload file"
          className="p-2 h-9 w-9 flex items-center justify-center"
        >
          <img src={uploadIcon} alt="Upload" className="w-5 h-5" />
        </Button>

        {canRemove && (
          <div className="fileUploadMeta">
            <span className="fileUploadFileName text-sm">File: {fileName}</span>
            <Button
              className="fileUploadRemoveButton p-2 h-8 w-8 flex items-center justify-center"
              variant="secondary"
              disabled={disabled}
              onClick={() => onRemove && onRemove()}
              aria-label="Remove file"
              title="Remove file"
            >
              <img src={deleteIcon} alt="Remove" className="w-4 h-4" />
            </Button>
          </div>
        )}
      </div>

      <div className="fileUploadControlHint text-sm">Upload PDF/TXT/CSV, then ask questions about the content.</div>
    </div>
  );
}
