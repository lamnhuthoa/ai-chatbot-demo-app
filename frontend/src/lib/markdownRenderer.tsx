import MarkdownIt from "markdown-it";
import highlight from "highlight.js";
import DOMPurify from "dompurify";
import parse from "html-react-parser";

const markdownRendererInstance = new MarkdownIt({
  linkify: true,
  breaks: true,
  highlight: (code, language) => {
    try {
      if (language && highlight.getLanguage(language)) {
        return highlight.highlight(code, { language }).value;
      }
      return highlight.highlightAuto(code).value;
    } catch {
      return markdownRendererInstance.utils.escapeHtml(code);
    }
  },
});

export function renderMarkdownToReact(markdownText: string) {
  const rawHtml = markdownRendererInstance.render(markdownText || "");
  const sanitizedHtml = DOMPurify.sanitize(rawHtml, { USE_PROFILES: { html: true } });
  return parse(sanitizedHtml);
}
