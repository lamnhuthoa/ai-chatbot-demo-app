export const DEFAULT_TITLE = "New chat";

export function generateTitleFromPrompt(prompt: string): string {
  let text = (prompt || "").trim().replace(/\n+/g, " ");
  if (!text) return DEFAULT_TITLE;
  const sentenceSplit = [". ", "? ", "! "];
  for (const sep of sentenceSplit) {
    if (text.includes(sep)) {
      text = text.split(sep, 1)[0];
      break;
    }
  }
  const words = text.split(/\s+/);
  if (words.length > 10) text = words.slice(0, 10).join(" ");
  if (text.length > 80) text = text.slice(0, 80).trimEnd();
  if (words.length > 10 || sentenceSplit.some((s) => (prompt || "").includes(s))) {
    if (!text.endsWith("...") && !text.endsWith("...")) text = text + "...";
  }
  return text || DEFAULT_TITLE;
}
