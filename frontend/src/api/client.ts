import axios from "axios";

// Use VITE_API_BASE if provided; fallback to current backend port 8000.
export const BASE_API_URL = (import.meta.env && import.meta.env.VITE_API_BASE) ? import.meta.env.VITE_API_BASE : "http://localhost:8000";

const httpClient = axios.create({
  baseURL: BASE_API_URL,
});

export { httpClient };
