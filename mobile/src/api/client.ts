import { clearTokens, getServerUrl, loadSession, saveTokens } from "./storage";
import type { AuthResponse } from "./types";

const TIMEOUT_MS = 15_000;

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields?: Record<string, string>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(fn: (() => void) | null) {
  onSessionExpired = fn;
}

type Options = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  auth?: boolean;
};

async function rawFetch(path: string, opts: Options, token: string | null): Promise<Response> {
  const base = await getServerUrl();
  if (!base) throw new ApiError(0, "no_server", "Configure o endereço do servidor na tela de login.");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    return await fetch(`${base}/api/v1${path}`, {
      method: opts.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(opts.body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...opts.headers,
      },
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(0, "network", "Sem conexão com o servidor. Tentaremos de novo.");
  } finally {
    clearTimeout(timer);
  }
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const data = await res.json();
    const e = data?.error;
    if (e && typeof e.message === "string") return new ApiError(res.status, String(e.code ?? "error"), e.message, e.fields);
  } catch {
    // corpo não era JSON
  }
  if (res.status === 429) return new ApiError(429, "rate_limited", "Muitas tentativas. Aguarde um pouco.");
  return new ApiError(res.status, "error", "Algo deu errado no servidor. Tente de novo.");
}

// Uma única renovação por vez, mesmo com várias requisições falhando juntas.
let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshing) {
    refreshing = (async () => {
      const { refresh } = await loadSession();
      if (!refresh) return null;
      const res = await rawFetch("/auth/refresh", { method: "POST", body: { refresh_token: refresh } }, null);
      if (!res.ok) {
        if (res.status === 401 || res.status === 400) return null;
        throw await toError(res);
      }
      const data = (await res.json()) as AuthResponse;
      await saveTokens(data.access_token, data.refresh_token);
      return data.access_token;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const auth = opts.auth ?? true;
  let token = auth ? (await loadSession()).access : null;
  let res = await rawFetch(path, opts, token);

  if (auth && res.status === 401) {
    token = await refreshAccessToken();
    if (!token) {
      await clearTokens();
      onSessionExpired?.();
      throw new ApiError(401, "unauthorized", "Sua sessão expirou. Entre novamente.");
    }
    res = await rawFetch(path, opts, token);
  }

  if (!res.ok) throw await toError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return "Algo deu errado. Tente de novo.";
}
