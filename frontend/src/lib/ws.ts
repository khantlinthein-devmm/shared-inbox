export function buildWsUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  if (explicit) return explicit;

  const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return `${api.replace(/^http/, "ws")}/api/v1/ws`;
}