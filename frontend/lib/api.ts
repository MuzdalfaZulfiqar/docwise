export const APP_NAME = "DocWise";
export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Doc = {
  id: string; filename: string; status: string; progress: number;
  error?: string | null; chunk_count?: number | null; pages?: number | null;
};
export type Source = {
  n: number; chunk_id: number; document_id: string; filename: string;
  page: number; heading?: string | null; snippet: string;
};
export type Usage = {
  model: string; input_tokens: number; output_tokens: number; embed_tokens: number;
  cost_usd: number; latency_ms: number;
};
export type Msg = {
  role: "user" | "assistant"; content: string; sources?: Source[]; usage?: Usage;
  status?: string; error?: string;
};
export type Conversation = { id: string; title: string; created_at: string };
export type Me = { email: string; daily_token_quota: number; tokens_used_today: number };
export type Passage = {
  id: number; idx: number; text: string; page: number; heading?: string | null;
  neighbors: { idx: number; text: string }[];
};
export type PassageView = { source: Source; passage: Passage | null };

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

async function readError(r: Response, fallback: string): Promise<string> {
  try {
    const j = await r.json();
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) return "Check your input and try again (passwords need 8+ characters).";
  } catch { /* not JSON */ }
  return fallback;
}

export async function api(path: string, token: string, init: RequestInit = {}): Promise<Response> {
  let r: Response;
  try {
    r = await fetch(API + path, { ...init, headers: { ...(init.headers || {}), Authorization: `Bearer ${token}` } });
  } catch {
    throw new ApiError("Can’t reach the server. Check that the API is running.", 0);
  }
  if (!r.ok) throw new ApiError(await readError(r, r.statusText || "Request failed"), r.status);
  return r;
}

export async function authCall(kind: "login" | "register", email: string, password: string): Promise<string> {
  let r: Response;
  try {
    r = await fetch(`${API}/auth/${kind}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
    });
  } catch {
    throw new ApiError("Can’t reach the server. Check that the API is running.", 0);
  }
  if (!r.ok) throw new ApiError(await readError(r, "Sign in failed"), r.status);
  return (await r.json()).token;
}

// Upload with progress (fetch can't report upload progress; XHR can)
export function upload(file: File, token: string, onProgress: (pct: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API}/documents`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => {
      if (xhr.status < 300) return resolve();
      let msg = "Upload failed";
      try { const d = JSON.parse(xhr.responseText).detail; if (typeof d === "string") msg = d; } catch { /* ignore */ }
      reject(new ApiError(msg, xhr.status));
    };
    xhr.onerror = () => reject(new ApiError("Can’t reach the server. Check that the API is running.", 0));
    const fd = new FormData();
    fd.append("file", file);
    xhr.send(fd);
  });
}

// POST + streamed SSE (EventSource can't send auth headers or POST bodies)
export async function streamChat(token: string, body: object, on: (event: string, data: any) => void) {
  const r = await api("/chat", token, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const reader = r.body!.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const raw = buf.slice(0, i);
      buf = buf.slice(i + 2);
      const ev = /event: (.*)/.exec(raw)?.[1];
      const data = /data: (.*)/.exec(raw)?.[1];
      if (ev && data) on(ev, JSON.parse(data));
    }
  }
}

// Open the original file at the cited page (needs the auth header, so fetch as a blob)
export async function openOriginal(docId: string, page: number, token: string) {
  const w = window.open("", "_blank"); // open synchronously so popup blockers allow it
  try {
    const blob = await (await api(`/documents/${docId}/file`, token)).blob();
    const url = URL.createObjectURL(blob);
    if (w) w.location.href = `${url}#page=${page}`;
  } catch (e) {
    w?.close();
    throw e;
  }
}
