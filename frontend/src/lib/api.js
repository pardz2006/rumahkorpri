import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({ baseURL: `${BASE}/api` });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("korpri_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const BACKEND = BASE;

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Terjadi kesalahan. Silakan coba lagi.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const rupiah = (v) => {
  if (v == null || isNaN(v)) return "Rp 0";
  return "Rp " + Math.round(v).toLocaleString("id-ID");
};

export const mediaUrl = (v) => {
  if (!v) return v;
  if (v.startsWith("data:") || v.startsWith("http")) return v;
  if (v.startsWith("/api/")) return `${BASE}${v}`;
  return v;
};
