export const formatAssistantMessage = (message) => {
    return message
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*\s/g, '<li>')
      .replace(/(\*\s?)([^\n]*)/g, '<li>$2</li>')
      .replace(/\n/g, '<br />');
  };