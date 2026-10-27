// src/api.js
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
let API_KEY = import.meta.env.VITE_API_KEY || "";

export function setApiKey(key) { API_KEY = key || ""; }

async function handleRes(res, path) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const err = new Error(`HTTP ${res.status} ${res.statusText} for ${path} — ${text}`);
    err.status = res.status;
    err.text = text;
    throw err;
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export async function getJSON(path) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, { headers: API_KEY ? { "x-api-key": API_KEY } : {} });
  return handleRes(res, url);
}

export async function postJSON(path, body) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(API_KEY ? { "x-api-key": API_KEY } : {}) },
    body: JSON.stringify(body),
  });
  return handleRes(res, url);
}

export async function uploadFile(path, file) {
  const url = `${API_BASE}${path}`;
  const form = new FormData();
  form.append("file", file, file.name || "upload.csv");
  const res = await fetch(url, { method: "POST", headers: API_KEY ? { "x-api-key": API_KEY } : {}, body: form });
  return handleRes(res, url);
}
