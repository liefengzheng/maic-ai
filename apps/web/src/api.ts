const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:3001";

export function apiUrl(path: string) {
  return `${apiBaseUrl}${path}`;
}
