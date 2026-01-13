export default function StatusBar(parameters: { sessionIdentifier: string; statusMessage: string | null }) {
  return (
    <div className="flex items-center justify-between text-sm text-muted-foreground">
      <div>Session: {parameters.sessionIdentifier.slice(0, 8)}...</div>
      {parameters.statusMessage && <div className="text-destructive">{parameters.statusMessage}</div>}
    </div>
  );
}
